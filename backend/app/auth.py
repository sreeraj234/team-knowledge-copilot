"""Authentication and On-Behalf-Of (OBO) token exchange routines for Entra ID.

Validates incoming access tokens, acquires downstream Microsoft Graph tokens
via the MSAL OBO flow, and resolves the user's transitive directory group
memberships for pre-retrieval access control.
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx
import jwt
import msal
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroupInfo:
    """Directory group metadata."""

    id: str
    display_name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class UserIdentity:
    """Resolved user identity with immutable directory OID and group memberships."""

    oid: str
    tenant_id: str
    groups: list[str] = field(default_factory=list)
    group_details: list[GroupInfo] = field(default_factory=list)
    upn: str | None = None
    name: str | None = None


# ---------------------------------------------------------------------------
# Custom Exceptions (Fail-Closed)
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base exception for all authentication and authorization failures."""


class TokenValidationError(AuthError):
    """Raised when an incoming user assertion fails validation checks."""


class OBOExchangeError(AuthError):
    """Raised when MSAL fails to exchange assertion for a Graph token."""


class GraphResolutionError(AuthError):
    """Raised when directory group resolution via Microsoft Graph fails."""


# ---------------------------------------------------------------------------
# JWKS Client Cache
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4)
def get_jwks_client(jwks_uri: str) -> jwt.PyJWKClient:
    """Return a cached PyJWKClient instance for the specified JWKS URI."""
    return jwt.PyJWKClient(jwks_uri, cache_keys=True, max_cached_keys=16, lifespan=3600)


# ---------------------------------------------------------------------------
# Token Validation
# ---------------------------------------------------------------------------


def validate_token(
    token: str,
    settings: Settings | None = None,
    jwks_client: jwt.PyJWKClient | None = None,
) -> dict[str, Any]:
    """Validate an incoming Bearer token from Entra ID.

    Verifies:
      - Valid RS256 signature using Entra ID public signing keys
      - Expected audience (API_CLIENT_ID or api://API_CLIENT_ID)
      - Expected issuer (https://login.microsoftonline.com/{TENANT_ID}/v2.0)
      - Required scope 'access_as_user' in the 'scp' claim
      - User identity extracted from 'oid' claim (never relying on 'sub')
      - Tenant ID matches TENANT_ID

    Raises:
      TokenValidationError: On any validation error (fail-closed).
    """
    if not token or not isinstance(token, str):
        raise TokenValidationError("Token must be a non-empty string")

    # Strip optional 'Bearer ' prefix if passed with prefix
    cleaned_token = token.strip()
    if cleaned_token.lower().startswith("bearer "):
        cleaned_token = cleaned_token[7:].strip()

    if not cleaned_token:
        raise TokenValidationError("Token is empty after stripping Bearer prefix")

    cfg = settings or get_settings()

    # 1. Fetch signing key from JWKS
    client = jwks_client or get_jwks_client(cfg.jwks_uri)
    try:
        signing_key = client.get_signing_key_from_jwt(cleaned_token)
    except (PyJWTError, Exception) as exc:
        logger.error("Failed to retrieve signing key for token: %s", exc)
        raise TokenValidationError(
            f"Unable to retrieve signing key from JWKS: {exc}"
        ) from exc

    # 2. Decode and verify JWT claims (signature, audience, issuer, expiration)
    try:
        payload = jwt.decode(
            cleaned_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=cfg.allowed_audiences,
            issuer=cfg.issuer,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
            },
        )
    except PyJWTError as exc:
        logger.error("JWT verification failed: %s", exc)
        raise TokenValidationError(f"JWT verification failed: {exc}") from exc

    # 3. Scope validation: require 'access_as_user'
    scp = payload.get("scp")
    if isinstance(scp, str):
        scopes = set(scp.split())
    elif isinstance(scp, (list, tuple, set)):
        scopes = set(scp)
    else:
        scopes = set()

    if "access_as_user" not in scopes:
        logger.error("Token missing required 'access_as_user' scope: %s", scopes)
        raise TokenValidationError(
            "Token does not contain required scope 'access_as_user'"
        )

    # 4. Identity extraction: extract 'oid', never rely on 'sub'
    oid = payload.get("oid")
    if not oid or not isinstance(oid, str) or not oid.strip():
        logger.error("Token missing valid 'oid' claim. Found: %s", oid)
        raise TokenValidationError("Token missing valid 'oid' (Object ID) claim")

    # 5. Tenant verification
    tid = payload.get("tid")
    if cfg.tenant_id and tid and tid.lower() != cfg.tenant_id.lower():
        logger.error("Token tenant '%s' != expected '%s'", tid, cfg.tenant_id)
        raise TokenValidationError("Token tenant ID does not match expected tenant")

    return payload


# ---------------------------------------------------------------------------
# On-Behalf-Of (OBO) Token Exchange
# ---------------------------------------------------------------------------


def exchange_obo_token(
    user_assertion: str,
    settings: Settings | None = None,
    cca: msal.ConfidentialClientApplication | None = None,
    scopes: list[str] | None = None,
) -> str:
    """Exchange incoming user token for Graph token via MSAL OBO flow.

    Args:
      user_assertion: The validated user access token.
      settings: Configuration settings (falls back to cached singleton).
      cca: Optional ConfidentialClientApplication instance (for mocking).
      scopes: Graph scopes to request (defaults to User.Read).

    Returns:
      access_token: The downstream Microsoft Graph access token.

    Raises:
      OBOExchangeError: If MSAL fails to acquire the OBO token (fail-closed).
    """
    cfg = settings or get_settings()
    app = cca or msal.ConfidentialClientApplication(
        client_id=cfg.api_client_id,
        client_credential=cfg.api_client_secret,
        authority=cfg.authority,
    )

    cleaned_assertion = user_assertion.strip()
    if cleaned_assertion.lower().startswith("bearer "):
        cleaned_assertion = cleaned_assertion[7:].strip()

    target_scopes = scopes or cfg.graph_scopes

    logger.debug("Initiating MSAL OBO token exchange for scopes: %s", target_scopes)
    result = app.acquire_token_on_behalf_of(
        user_assertion=cleaned_assertion,
        scopes=target_scopes,
    )

    if not isinstance(result, dict) or "access_token" not in result:
        error = (
            result.get("error", "unknown_error")
            if isinstance(result, dict)
            else str(result)
        )
        desc = (
            result.get("error_description", "No description provided")
            if isinstance(result, dict)
            else ""
        )
        logger.error("MSAL OBO exchange failed: error=%s, desc=%s", error, desc)
        raise OBOExchangeError(f"OBO token exchange failed: {error} - {desc}")

    return result["access_token"]


# ---------------------------------------------------------------------------
# Transitive Group Resolution via Microsoft Graph
# ---------------------------------------------------------------------------


def resolve_user_groups(
    graph_token: str,
    http_client: httpx.Client | None = None,
    endpoint: str = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf",
) -> tuple[list[str], list[GroupInfo]]:
    """Query Microsoft Graph /v1.0/me/transitiveMemberOf to resolve user groups.

    Follows @odata.nextLink pagination to ensure complete group enumeration.
    Fails closed on any HTTP or network error.

    Returns:
      (group_ids, group_details): Group ID strings and GroupInfo objects.

    Raises:
      GraphResolutionError: If the Graph request fails (fail-closed).
    """
    headers = {
        "Authorization": f"Bearer {graph_token}",
        "Accept": "application/json",
        "ConsistencyLevel": "eventual",
    }

    group_ids: list[str] = []
    group_details: list[GroupInfo] = []
    seen_ids: set[str] = set()
    next_url: str | None = endpoint

    def _fetch_pages(client: httpx.Client) -> None:
        nonlocal next_url
        while next_url:
            try:
                response = client.get(next_url, headers=headers)
            except httpx.RequestError as exc:
                logger.error(
                    "Network error querying Graph API at %s: %s", next_url, exc
                )
                raise GraphResolutionError(
                    f"Network error querying Microsoft Graph: {exc}"
                ) from exc

            if response.status_code != 200:
                logger.error(
                    "Graph API request to %s failed with status %d: %s",
                    next_url,
                    response.status_code,
                    response.text,
                )
                raise GraphResolutionError(
                    f"Graph API request failed with status {response.status_code}: "
                    f"{response.text}"
                )

            try:
                data = response.json()
            except Exception as exc:
                logger.error("Failed to parse JSON response from Graph API: %s", exc)
                raise GraphResolutionError(
                    "Malformed JSON response from Microsoft Graph"
                ) from exc

            for item in data.get("value", []):
                odata_type = item.get("@odata.type", "")
                # Only include directory group objects
                is_group = (
                    odata_type == "#microsoft.graph.group"
                    or odata_type.endswith(".group")
                    or not odata_type
                )
                if is_group:
                    gid = item.get("id")
                    if gid and gid not in seen_ids:
                        seen_ids.add(gid)
                        group_ids.append(gid)
                        group_details.append(
                            GroupInfo(
                                id=gid,
                                display_name=item.get("displayName"),
                                description=item.get("description"),
                            )
                        )

            next_url = data.get("@odata.nextLink")

    if http_client is not None:
        _fetch_pages(http_client)
    else:
        with httpx.Client(timeout=15.0) as client:
            _fetch_pages(client)

    return group_ids, group_details


# ---------------------------------------------------------------------------
# High-Level Orchestrator
# ---------------------------------------------------------------------------


def authenticate_and_resolve(
    user_token: str,
    settings: Settings | None = None,
    jwks_client: jwt.PyJWKClient | None = None,
    cca: msal.ConfidentialClientApplication | None = None,
    http_client: httpx.Client | None = None,
) -> UserIdentity:
    """Validate user token, perform OBO exchange, and resolve group memberships.

    Ensures strict fail-closed behavior at every step.

    Returns:
      UserIdentity: Verified identity with oid, tenant_id, and resolved group IDs.

    Raises:
      AuthError: If any step fails.
    """
    cfg = settings or get_settings()

    # Step 1: Validate incoming user token
    claims = validate_token(user_token, settings=cfg, jwks_client=jwks_client)
    oid = claims["oid"]
    tenant_id = claims.get("tid", cfg.tenant_id)

    # Step 2: MSAL OBO exchange for Graph token
    graph_token = exchange_obo_token(user_token, settings=cfg, cca=cca)

    # Step 3: Query Graph for transitive group memberships
    group_ids, group_details = resolve_user_groups(graph_token, http_client=http_client)

    return UserIdentity(
        oid=oid,
        tenant_id=tenant_id,
        groups=group_ids,
        group_details=group_details,
        upn=claims.get("preferred_username") or claims.get("upn"),
        name=claims.get("name"),
    )


# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------

_bearer_security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_security),
) -> UserIdentity:
    """FastAPI dependency to authenticate and resolve group memberships.

    Raises:
      HTTPException(401): If token is missing, invalid, or OBO/Graph lookup fails.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return authenticate_and_resolve(credentials.credentials)
    except AuthError as exc:
        logger.warning("Authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
