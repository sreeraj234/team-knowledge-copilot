"""Entra ID token validation, OBO exchange, and Graph group resolution."""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import httpx
import jwt
import msal
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
_GRAPH_GROUPS_URL = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf"
_GRAPH_SCOPE = "https://graph.microsoft.com/User.Read"


@dataclass(frozen=True)
class GroupInfo:
    id: str
    display_name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class UserIdentity:
    oid: str
    tenant_id: str
    groups: list[str] = field(default_factory=list)
    group_details: list[GroupInfo] = field(default_factory=list)
    upn: str | None = None
    name: str | None = None


class AuthError(Exception):
    """Base class for authentication and authorization failures."""


class TokenValidationError(AuthError):
    """The supplied API access token is invalid."""


class OBOExchangeError(AuthError):
    """MSAL could not exchange the user assertion."""


class GraphResolutionError(AuthError):
    """Microsoft Graph group resolution failed."""


@lru_cache(maxsize=4)
def get_jwks_client(jwks_uri: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_uri, cache_keys=True, max_cached_keys=16)


def validate_token(
    token: str,
    settings: Settings | None = None,
    jwks_client: jwt.PyJWKClient | None = None,
) -> dict[str, Any]:
    """Verify an API token's signature, issuer, audience, scope, and OID."""
    if not isinstance(token, str) or not token.strip():
        raise TokenValidationError("Token must be a non-empty string")

    cleaned_token = token.strip()
    if cleaned_token.lower().startswith("bearer "):
        cleaned_token = cleaned_token[7:].strip()
    if not cleaned_token:
        raise TokenValidationError("Token must be a non-empty string")

    cfg = settings or get_settings()
    try:
        client = jwks_client or get_jwks_client(cfg.jwks_uri)
        signing_key = client.get_signing_key_from_jwt(cleaned_token)
        claims = jwt.decode(
            cleaned_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=cfg.allowed_audiences,
            issuer=cfg.issuer,
        )
    except Exception as exc:
        logger.info("API token validation failed: %s", type(exc).__name__)
        raise TokenValidationError("Token signature or claims are invalid") from exc

    scope_claim = claims.get("scp")
    scopes = scope_claim.split() if isinstance(scope_claim, str) else []
    if "access_as_user" not in scopes:
        raise TokenValidationError("Token is missing the access_as_user scope")
    oid = claims.get("oid")
    if not isinstance(oid, str) or not oid.strip():
        raise TokenValidationError("Token is missing a valid oid claim")
    tenant_id = claims.get("tid")
    if not isinstance(tenant_id, str) or tenant_id.lower() != cfg.tenant_id.lower():
        raise TokenValidationError("Token tenant does not match the configured tenant")

    return claims


def exchange_obo_token(
    user_assertion: str,
    settings: Settings | None = None,
    cca: msal.ConfidentialClientApplication | None = None,
) -> str:
    """Exchange a validated user assertion for a Microsoft Graph access token."""
    if not isinstance(user_assertion, str) or not user_assertion.strip():
        raise OBOExchangeError("A user assertion is required for OBO exchange")
    cfg = settings or get_settings()
    cleaned_assertion = user_assertion.strip()
    if cleaned_assertion.lower().startswith("bearer "):
        cleaned_assertion = cleaned_assertion[7:].strip()
    try:
        app = cca or msal.ConfidentialClientApplication(
            client_id=cfg.api_client_id,
            client_credential=cfg.api_client_secret,
            authority=cfg.authority,
        )
        result = app.acquire_token_on_behalf_of(
            user_assertion=cleaned_assertion,
            scopes=[_GRAPH_SCOPE],
        )
    except Exception as exc:
        logger.warning("MSAL OBO exchange failed: %s", type(exc).__name__)
        raise OBOExchangeError("MSAL OBO token exchange failed") from exc

    access_token = result.get("access_token") if isinstance(result, dict) else None
    if not isinstance(access_token, str) or not access_token:
        raise OBOExchangeError("MSAL OBO token exchange failed")
    return access_token


def resolve_user_groups(
    graph_token: str,
    http_client: httpx.Client | None = None,
) -> tuple[list[str], list[GroupInfo]]:
    """Retrieve all transitive group memberships, following Graph pagination."""
    if not isinstance(graph_token, str) or not graph_token.strip():
        raise GraphResolutionError("A Graph access token is required")
    headers = {
        "Authorization": "Bearer " + graph_token,
        "Accept": "application/json",
        "ConsistencyLevel": "eventual",
    }
    group_ids: list[str] = []
    details: list[GroupInfo] = []
    seen: set[str] = set()
    next_url: str | None = _GRAPH_GROUPS_URL
    owns_client = http_client is None
    client = http_client or httpx.Client(timeout=15.0)

    try:
        while next_url:
            parsed_url = urlparse(next_url)
            if (
                parsed_url.scheme != "https"
                or parsed_url.netloc != "graph.microsoft.com"
            ):
                raise GraphResolutionError("Graph returned an invalid pagination URL")
            try:
                response = client.get(next_url, headers=headers)
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning(
                    "Microsoft Graph group lookup failed: %s", type(exc).__name__
                )
                raise GraphResolutionError(
                    "Microsoft Graph group lookup failed"
                ) from exc

            if not isinstance(data, dict) or not isinstance(data.get("value"), list):
                raise GraphResolutionError(
                    "Microsoft Graph returned an invalid response"
                )
            for item in data["value"]:
                if not isinstance(item, dict):
                    raise GraphResolutionError(
                        "Microsoft Graph returned an invalid group"
                    )
                if item.get("@odata.type") != "#microsoft.graph.group":
                    continue
                group_id = item.get("id")
                if isinstance(group_id, str) and group_id and group_id not in seen:
                    seen.add(group_id)
                    group_ids.append(group_id)
                    details.append(
                        GroupInfo(
                            id=group_id,
                            display_name=item.get("displayName"),
                            description=item.get("description"),
                        )
                    )
            next_url = data.get("@odata.nextLink")
            if next_url is not None and not isinstance(next_url, str):
                raise GraphResolutionError(
                    "Microsoft Graph returned an invalid pagination URL"
                )
    finally:
        if owns_client:
            client.close()

    return group_ids, details


def authenticate_and_resolve(
    user_token: str,
    settings: Settings | None = None,
    jwks_client: jwt.PyJWKClient | None = None,
    cca: msal.ConfidentialClientApplication | None = None,
    http_client: httpx.Client | None = None,
) -> UserIdentity:
    """Validate a user token, perform OBO, and fetch transitive group IDs."""
    cfg = settings or get_settings()
    claims = validate_token(user_token, settings=cfg, jwks_client=jwks_client)
    graph_token = exchange_obo_token(user_token, settings=cfg, cca=cca)
    group_ids, group_details = resolve_user_groups(graph_token, http_client=http_client)
    return UserIdentity(
        oid=claims["oid"],
        tenant_id=claims["tid"],
        groups=group_ids,
        group_details=group_details,
        upn=claims.get("preferred_username") or claims.get("upn"),
        name=claims.get("name"),
    )


_bearer_security = HTTPBearer(auto_error=False)
_credentials_dependency = Depends(_bearer_security)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = _credentials_dependency,
) -> UserIdentity:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return authenticate_and_resolve(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
