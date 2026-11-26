#!/usr/bin/env python3
"""Smoke-test delegated Graph access using Entra device-code and OBO flows."""

import argparse
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import msal  # noqa: E402
from app.auth import AuthError, authenticate_and_resolve  # noqa: E402
from app.config import get_settings  # noqa: E402


def run_device_code_flow(client_id: str, authority: str, scope: str) -> str:
    app = msal.PublicClientApplication(client_id=client_id, authority=authority)
    flow = app.initiate_device_flow(scopes=[scope])
    if "user_code" not in flow:
        raise RuntimeError(
            flow.get("error_description", "Could not start device-code authentication")
        )
    print(flow.get("message", "Complete sign-in using the device code shown above."))
    result = app.acquire_token_by_device_flow(flow)
    token = result.get("access_token")
    if not token:
        raise RuntimeError(
            result.get("error_description", "Device-code sign-in failed")
        )
    return token


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MSAL device-code OBO smoke test")
    parser.add_argument("--token", help="Use an already-acquired API access token")
    parser.add_argument("--client-id", help="Public client ID for device-code sign-in")
    args = parser.parse_args(argv)
    settings = get_settings()

    if not settings.tenant_id or not settings.api_client_id:
        parser.error("TENANT_ID and API_CLIENT_ID must be configured")

    try:
        token = args.token
        if token is None:
            client_id = args.client_id or settings.test_client_id
            if not client_id:
                parser.error("Set TEST_CLIENT_ID or pass --client-id")
            token = run_device_code_flow(
                client_id, settings.authority, settings.api_scope
            )
        identity = authenticate_and_resolve(token, settings=settings)
    except (AuthError, RuntimeError) as exc:
        print(f"Authentication or Graph lookup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"User OID: {identity.oid}")
    print("Resolved group IDs:")
    for group_id in identity.groups:
        print(group_id)


if __name__ == "__main__":
    main()
