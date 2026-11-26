from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import httpx
import jwt
import pytest
from app.auth import (
    GraphResolutionError,
    TokenValidationError,
    authenticate_and_resolve,
    resolve_user_groups,
    validate_token,
)
from app.config import Settings
from cryptography.hazmat.primitives.asymmetric import rsa

TENANT_ID = "00000000-0000-0000-0000-000000000001"
CLIENT_ID = "00000000-0000-0000-0000-000000000002"
USER_OID = "11111111-1111-1111-1111-111111111111"
GROUP_A = "22222222-2222-2222-2222-222222222222"
GROUP_B = "33333333-3333-3333-3333-333333333333"


@pytest.fixture
def token_setup():
    settings = Settings(TENANT_ID=TENANT_ID, API_CLIENT_ID=CLIENT_ID)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks_client = MagicMock()
    signing_key = MagicMock()
    signing_key.key = private_key.public_key()
    jwks_client.get_signing_key_from_jwt.return_value = signing_key
    claims = {
        "iss": settings.issuer,
        "aud": CLIENT_ID,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "tid": TENANT_ID,
        "oid": USER_OID,
        "sub": "do-not-use-sub",
        "scp": "access_as_user",
    }
    token = jwt.encode(claims, private_key, algorithm="RS256")
    return settings, token, jwks_client


def test_validate_token_checks_scope_and_uses_oid(token_setup):
    settings, token, jwks_client = token_setup

    claims = validate_token(token, settings, jwks_client)

    assert claims["oid"] == USER_OID
    assert claims["oid"] != claims["sub"]


def test_validate_token_rejects_missing_scope(token_setup):
    settings, token, jwks_client = token_setup
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["scp"] = "User.Read"
    invalid_token = jwt.encode(claims, signing_key, algorithm="RS256")
    jwks_client.get_signing_key_from_jwt.return_value.key = signing_key.public_key()

    with pytest.raises(TokenValidationError, match="access_as_user"):
        validate_token(invalid_token, settings, jwks_client)


def test_authenticate_and_resolve_exchanges_and_paginates(token_setup):
    settings, token, jwks_client = token_setup
    cca = MagicMock()
    cca.acquire_token_on_behalf_of.return_value = {"access_token": "graph-token"}
    client = MagicMock(spec=httpx.Client)
    first_page = MagicMock(status_code=200)
    first_page.json.return_value = {
        "@odata.nextLink": (
            "https://graph.microsoft.com/v1.0/me/transitiveMemberOf?$skiptoken=next"
        ),
        "value": [{"@odata.type": "#microsoft.graph.group", "id": GROUP_A}],
    }
    second_page = MagicMock(status_code=200)
    second_page.json.return_value = {
        "value": [{"@odata.type": "#microsoft.graph.group", "id": GROUP_B}]
    }
    client.get.side_effect = [first_page, second_page]

    identity = authenticate_and_resolve(token, settings, jwks_client, cca, client)

    assert identity.oid == USER_OID
    assert identity.groups == [GROUP_A, GROUP_B]
    cca.acquire_token_on_behalf_of.assert_called_once_with(
        user_assertion=token,
        scopes=["https://graph.microsoft.com/User.Read"],
    )
    assert client.get.call_count == 2
    assert (
        client.get.call_args_list[0]
        .kwargs["headers"]["Authorization"]
        .startswith("Bearer ")
    )
    assert (
        client.get.call_args_list[0]
        .kwargs["headers"]["Authorization"]
        .endswith("graph-token")
    )


def test_graph_failure_fails_closed():
    response = MagicMock(status_code=403, text="Forbidden")
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "forbidden", request=MagicMock(), response=response
    )
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = response

    with pytest.raises(GraphResolutionError):
        resolve_user_groups("graph-token", client)
