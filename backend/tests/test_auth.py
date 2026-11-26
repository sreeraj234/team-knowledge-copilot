"""Tests for Entra ID token validation, MSAL OBO exchange, and group resolution."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import jwt
import pytest
from app.auth import (
    AuthError,
    GraphResolutionError,
    OBOExchangeError,
    TokenValidationError,
    authenticate_and_resolve,
    exchange_obo_token,
    get_current_user,
    resolve_user_groups,
    validate_token,
)
from app.config import Settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt.exceptions import PyJWKClientError

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"
TEST_API_CLIENT_ID = "00000000-0000-0000-0000-000000000002"
TEST_API_CLIENT_SECRET = "mock_secret_value"
TEST_USER_OID = "11111111-1111-1111-1111-111111111111"
TEST_TEAM_A_GROUP_ID = "22222222-2222-2222-2222-222222222222"
TEST_TEAM_B_GROUP_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings instance populated with known test UUIDs."""
    return Settings(
        TENANT_ID=TEST_TENANT_ID,
        API_CLIENT_ID=TEST_API_CLIENT_ID,
        API_CLIENT_SECRET=TEST_API_CLIENT_SECRET,
        TEST_CLIENT_ID="00000000-0000-0000-0000-000000000003",
        LUKE_OID=TEST_USER_OID,
        TEAM_A_GROUP_ID=TEST_TEAM_A_GROUP_ID,
        TEAM_B_GROUP_ID=TEST_TEAM_B_GROUP_ID,
    )


@pytest.fixture(scope="session")
def rsa_keypair():
    """Generate an ephemeral RSA key pair for signing and verifying test JWTs."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    return private_pem, public_key


@pytest.fixture
def mock_jwks_client(rsa_keypair):
    """Mock PyJWKClient that returns the session test public key."""
    _, public_key = rsa_keypair
    client = MagicMock()
    signing_key = MagicMock()
    signing_key.key = public_key
    client.get_signing_key_from_jwt.return_value = signing_key
    return client


def make_jwt(
    rsa_keypair,
    test_settings: Settings,
    *,
    oid: str | None = TEST_USER_OID,
    aud: str | None = None,
    iss: str | None = None,
    scp: str | list[str] | None = "access_as_user",
    tid: str | None = None,
    expired: bool = False,
    extra_claims: dict | None = None,
) -> str:
    """Helper to generate signed RS256 test JWTs."""
    private_pem, _ = rsa_keypair
    now = datetime.now(UTC)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)

    payload = {
        "exp": int(exp.timestamp()),
        "nbf": int((now - timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": iss or test_settings.issuer,
        "aud": aud or test_settings.api_client_id,
        "sub": "pairwise_sub_to_ignore",
    }
    if oid is not None:
        payload["oid"] = oid
    if scp is not None:
        payload["scp"] = scp
    if tid is not None:
        payload["tid"] = tid
    else:
        payload["tid"] = test_settings.tenant_id

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, private_pem, algorithm="RS256")


# ===========================================================================
# 1. Token Validation Tests
# ===========================================================================


def test_validate_token_success(rsa_keypair, test_settings, mock_jwks_client):
    """Valid token with expected audience, issuer, scope, and oid passes."""
    token = make_jwt(rsa_keypair, test_settings)
    claims = validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)
    assert claims["oid"] == TEST_USER_OID
    assert claims["aud"] == test_settings.api_client_id
    assert claims["iss"] == test_settings.issuer
    assert "access_as_user" in claims["scp"]


def test_validate_token_with_api_prefix_audience(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Token with audience 'api://<API_CLIENT_ID>' is valid."""
    token = make_jwt(
        rsa_keypair,
        test_settings,
        aud=f"api://{test_settings.api_client_id}",
    )
    claims = validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)
    assert claims["oid"] == TEST_USER_OID


def test_validate_token_bearer_prefix_stripping(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Passing 'Bearer <token>' is stripped and accepted."""
    token = make_jwt(rsa_keypair, test_settings)
    claims = validate_token(
        f"Bearer {token}", settings=test_settings, jwks_client=mock_jwks_client
    )
    assert claims["oid"] == TEST_USER_OID


def test_validate_token_empty_fails():
    """Empty or whitespace token fails closed."""
    with pytest.raises(TokenValidationError, match="non-empty string"):
        validate_token("")
    with pytest.raises(TokenValidationError):
        validate_token("Bearer   ")


def test_validate_token_expired_fails(rsa_keypair, test_settings, mock_jwks_client):
    """Expired token fails closed."""
    token = make_jwt(rsa_keypair, test_settings, expired=True)
    with pytest.raises(TokenValidationError, match="JWT verification failed"):
        validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)


def test_validate_token_wrong_audience_fails(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Token issued for another API audience fails closed."""
    token = make_jwt(rsa_keypair, test_settings, aud="different-api-client-id")
    with pytest.raises(TokenValidationError, match="JWT verification failed"):
        validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)


def test_validate_token_wrong_issuer_fails(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Token from another tenant issuer fails closed."""
    token = make_jwt(
        rsa_keypair,
        test_settings,
        iss="https://login.microsoftonline.com/attacker-tenant/v2.0",
    )
    with pytest.raises(TokenValidationError, match="JWT verification failed"):
        validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)


def test_validate_token_missing_scope_fails(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Token missing required 'access_as_user' scope fails closed."""
    token = make_jwt(rsa_keypair, test_settings, scp="User.Read Mail.Read")
    with pytest.raises(TokenValidationError, match="access_as_user"):
        validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)


def test_validate_token_missing_oid_fails_even_with_sub(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Token missing 'oid' claim fails closed.

    'sub' must never be trusted as identity.
    """
    token = make_jwt(rsa_keypair, test_settings, oid=None)
    with pytest.raises(TokenValidationError, match="missing valid 'oid'"):
        validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)


def test_validate_token_tenant_mismatch_fails(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Token with tid different from configured tenant fails closed."""
    token = make_jwt(
        rsa_keypair,
        test_settings,
        tid="99999999-9999-9999-9999-999999999999",
    )
    with pytest.raises(TokenValidationError, match="Token tenant ID"):
        validate_token(token, settings=test_settings, jwks_client=mock_jwks_client)


def test_validate_token_jwks_failure_fails_closed(rsa_keypair, test_settings):
    """JWKS client network failure fails closed."""
    client = MagicMock()
    client.get_signing_key_from_jwt.side_effect = PyJWKClientError("Connection refused")
    token = make_jwt(rsa_keypair, test_settings)
    with pytest.raises(TokenValidationError, match="Unable to retrieve signing key"):
        validate_token(token, settings=test_settings, jwks_client=client)


# ===========================================================================
# 2. MSAL OBO Exchange Tests
# ===========================================================================


def test_exchange_obo_token_success(test_settings):
    """Successful MSAL OBO exchange returns the Graph access token."""
    mock_cca = MagicMock()
    mock_cca.acquire_token_on_behalf_of.return_value = {
        "access_token": "mock_graph_access_token_xyz",
        "token_type": "Bearer",
    }

    graph_token = exchange_obo_token(
        "test_user_assertion",
        settings=test_settings,
        cca=mock_cca,
    )
    assert graph_token == "mock_graph_access_token_xyz"
    mock_cca.acquire_token_on_behalf_of.assert_called_once_with(
        user_assertion="test_user_assertion",
        scopes=test_settings.graph_scopes,
    )


def test_exchange_obo_token_error_fails_closed(test_settings):
    """MSAL error in acquire_token_on_behalf_of raises OBOExchangeError."""
    mock_cca = MagicMock()
    mock_cca.acquire_token_on_behalf_of.return_value = {
        "error": "invalid_grant",
        "error_description": "AADSTS50013: Assertion is invalid",
    }

    with pytest.raises(OBOExchangeError, match="invalid_grant"):
        exchange_obo_token(
            "test_user_assertion",
            settings=test_settings,
            cca=mock_cca,
        )


def test_exchange_obo_token_missing_token_fails_closed(test_settings):
    """Response missing 'access_token' raises OBOExchangeError."""
    mock_cca = MagicMock()
    mock_cca.acquire_token_on_behalf_of.return_value = {"token_type": "Bearer"}

    with pytest.raises(OBOExchangeError, match="OBO token exchange failed"):
        exchange_obo_token(
            "test_user_assertion",
            settings=test_settings,
            cca=mock_cca,
        )


# ===========================================================================
# 3. Graph Group Resolution & Pagination Tests
# ===========================================================================


def test_resolve_user_groups_single_page():
    """Extracts directory groups and skips directory roles."""
    graph_response = {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#directoryObjects",
        "value": [
            {
                "@odata.type": "#microsoft.graph.group",
                "id": TEST_TEAM_A_GROUP_ID,
                "displayName": "team-a",
                "description": "Team A Engineers",
            },
            {
                "@odata.type": "#microsoft.graph.directoryRole",
                "id": "role-id-to-exclude",
                "displayName": "Directory Readers",
            },
        ],
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = graph_response
    mock_client.get.return_value = mock_resp

    group_ids, group_details = resolve_user_groups(
        "mock_graph_token", http_client=mock_client
    )

    assert group_ids == [TEST_TEAM_A_GROUP_ID]
    assert len(group_details) == 1
    assert group_details[0].id == TEST_TEAM_A_GROUP_ID
    assert group_details[0].display_name == "team-a"


def test_resolve_user_groups_pagination():
    """Follows @odata.nextLink across multiple pages."""
    page_1 = {
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/transitiveMemberOf?$skiptoken=page2",
        "value": [
            {
                "@odata.type": "#microsoft.graph.group",
                "id": TEST_TEAM_A_GROUP_ID,
                "displayName": "team-a",
            }
        ],
    }
    page_2 = {
        "value": [
            {
                "@odata.type": "#microsoft.graph.group",
                "id": TEST_TEAM_B_GROUP_ID,
                "displayName": "team-b",
            }
        ]
    }

    resp1 = MagicMock(status_code=200)
    resp1.json.return_value = page_1
    resp2 = MagicMock(status_code=200)
    resp2.json.return_value = page_2

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [resp1, resp2]

    group_ids, group_details = resolve_user_groups(
        "mock_graph_token", http_client=mock_client
    )

    assert group_ids == [TEST_TEAM_A_GROUP_ID, TEST_TEAM_B_GROUP_ID]
    assert len(group_details) == 2
    assert mock_client.get.call_count == 2


def test_resolve_user_groups_http_error_fails_closed():
    """HTTP 401/403 from Graph raises GraphResolutionError."""
    resp = MagicMock(status_code=403, text="Forbidden")
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = resp

    with pytest.raises(GraphResolutionError, match="status 403"):
        resolve_user_groups("mock_graph_token", http_client=mock_client)


def test_resolve_user_groups_network_error_fails_closed():
    """Network connection error raises GraphResolutionError."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ConnectError("Network is unreachable")

    with pytest.raises(GraphResolutionError, match="Network error"):
        resolve_user_groups("mock_graph_token", http_client=mock_client)


# ===========================================================================
# 4. Orchestrator Integration Tests
# ===========================================================================


def test_authenticate_and_resolve_end_to_end(
    rsa_keypair, test_settings, mock_jwks_client
):
    """End-to-end resolution returns populated UserIdentity."""
    token = make_jwt(
        rsa_keypair,
        test_settings,
        extra_claims={
            "preferred_username": "alice@tenant.onmicrosoft.com",
            "name": "Alice Developer",
        },
    )

    mock_cca = MagicMock()
    mock_cca.acquire_token_on_behalf_of.return_value = {
        "access_token": "graph_obo_token_for_alice"
    }

    mock_http_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "value": [
            {
                "@odata.type": "#microsoft.graph.group",
                "id": TEST_TEAM_A_GROUP_ID,
                "displayName": "team-a",
            }
        ]
    }
    mock_http_client.get.return_value = mock_resp

    identity = authenticate_and_resolve(
        token,
        settings=test_settings,
        jwks_client=mock_jwks_client,
        cca=mock_cca,
        http_client=mock_http_client,
    )

    assert identity.oid == TEST_USER_OID
    assert identity.tenant_id == TEST_TENANT_ID
    assert identity.groups == [TEST_TEAM_A_GROUP_ID]
    assert identity.upn == "alice@tenant.onmicrosoft.com"
    assert identity.name == "Alice Developer"


def test_authenticate_and_resolve_fails_closed_on_error(
    rsa_keypair, test_settings, mock_jwks_client
):
    """Failure at OBO step raises AuthError."""
    token = make_jwt(rsa_keypair, test_settings)
    mock_cca = MagicMock()
    mock_cca.acquire_token_on_behalf_of.return_value = {"error": "interaction_required"}

    with pytest.raises(AuthError):
        authenticate_and_resolve(
            token,
            settings=test_settings,
            jwks_client=mock_jwks_client,
            cca=mock_cca,
        )


# ===========================================================================
# 5. FastAPI Dependency Tests
# ===========================================================================


def test_get_current_user_missing_credentials_raises_401():
    """Missing Authorization header raises HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token_raises_401():
    """Invalid token raises HTTP 401."""
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad_token")
    with patch(
        "app.auth.authenticate_and_resolve",
        side_effect=TokenValidationError("Invalid token"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(creds)
        assert exc_info.value.status_code == 401
