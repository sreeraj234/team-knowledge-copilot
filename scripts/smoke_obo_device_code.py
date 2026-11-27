#!/usr/bin/env python3
"""Device-code flow smoke test for MSAL On-Behalf-Of (OBO) token exchange.

Signs in a test user interactively via MSAL device-code flow, requests an access token
for the backend API (api://<API_CLIENT_ID>/access_as_user), validates the token,
exchanges it for a downstream Microsoft Graph token via OBO, and prints the user's
immutable OID and resolved transitive directory group IDs.

Usage:
    python scripts/smoke_obo_device_code.py
    python scripts/smoke_obo_device_code.py --token <existing_access_token>
"""

import argparse
import sys
from pathlib import Path

# Ensure backend/ is in sys.path so app modules can be imported
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import msal  # noqa: E402
from app.auth import AuthError, authenticate_and_resolve  # noqa: E402
from app.config import get_settings  # noqa: E402


def run_device_code_flow(client_id: str, authority: str, scope: str) -> str:
    """Execute interactive device-code flow using MSAL PublicClientApplication."""
    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=authority,
    )

    flow = app.initiate_device_flow(scopes=[scope])
    if "user_code" not in flow:
        error = flow.get("error", "unknown_error")
        desc = flow.get("error_description", "Failed to initiate device-code flow")
        print(f"Error initiating device flow: {error} - {desc}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Microsoft Entra ID Device Code Authentication")
    print("=" * 70)
    msg = flow.get(
        "message",
        f"Open {flow['verification_uri']} and enter code {flow['user_code']}",
    )
    print(msg)
    print("=" * 70 + "\n")
    print("Waiting for authentication in browser...")

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        error = result.get("error", "auth_failed")
        desc = result.get(
            "error_description", "Failed to acquire token from device-code flow"
        )
        print(f"Authentication failed: {error} - {desc}", file=sys.stderr)
        sys.exit(1)

    return result["access_token"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MSAL Device Code & OBO Smoke Test",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Optional pre-acquired access token to test validation and OBO exchange",
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default=None,
        help="Public client ID for device flow (defaults to TEST_CLIENT_ID)",
    )
    args = parser.parse_args()

    settings = get_settings()

    if not settings.tenant_id:
        print("Error: TENANT_ID is not configured in .env", file=sys.stderr)
        sys.exit(1)
    if not settings.api_client_id:
        print("Error: API_CLIENT_ID is not configured in .env", file=sys.stderr)
        sys.exit(1)

    client_id = args.client_id or settings.test_client_id
    if not args.token and not client_id:
        print(
            "Error: TEST_CLIENT_ID is not configured and --client-id was not passed",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.token:
        print("Using provided access token from command line arguments...")
        token = args.token
    else:
        scope = settings.api_scope
        print(f"Initiating device code sign-in for scope: {scope}")
        token = run_device_code_flow(
            client_id=client_id,
            authority=settings.authority,
            scope=scope,
        )

    print("\nValidating token and executing On-Behalf-Of (OBO) group resolution...")
    try:
        identity = authenticate_and_resolve(token, settings=settings)
    except AuthError as exc:
        print(
            f"\nAuthentication or OBO exchange failed (fail-closed): {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\n" + "=" * 70)
    print("OBO Token Exchange & Directory Group Resolution Succeeded")
    print("=" * 70)
    print(f"User OID:        {identity.oid}")
    print(f"Tenant ID:       {identity.tenant_id}")
    if identity.upn:
        print(f"User Principal:  {identity.upn}")
    if identity.name:
        print(f"Display Name:    {identity.name}")

    print(f"\nResolved Group IDs ({len(identity.groups)} total):")
    if not identity.groups:
        print("  (None)")
    else:
        for grp in identity.group_details:
            name_str = f" ({grp.display_name})" if grp.display_name else ""
            print(f"  - {grp.id}{name_str}")

    # Acceptance criteria verification helpers
    print("\nVerification Checks:")
    if settings.luke_oid and identity.oid.lower() == settings.luke_oid.lower():
        print("  [MATCH] User OID matches Alice/Luke test identity")
    elif settings.leia_oid and identity.oid.lower() == settings.leia_oid.lower():
        print("  [MATCH] User OID matches Bob/Leia test identity")
    else:
        print(f"  [INFO] User OID: {identity.oid}")

    if settings.team_a_group_id and settings.team_a_group_id in identity.groups:
        print(
            f"  [MATCH] User is confirmed member of team-a ({settings.team_a_group_id})"
        )
    elif settings.team_b_group_id and settings.team_b_group_id in identity.groups:
        print(
            f"  [MATCH] User is confirmed member of team-b ({settings.team_b_group_id})"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
