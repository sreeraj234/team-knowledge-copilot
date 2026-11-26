"""Tests for scripts/smoke_obo_device_code.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root and backend are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.auth import GroupInfo, UserIdentity  # noqa: E402
from app.config import Settings  # noqa: E402

from scripts.smoke_obo_device_code import (  # noqa: E402
    main,
    run_device_code_flow,
)


def test_run_device_code_flow_success():
    """Device code flow acquires access token upon user authentication."""
    mock_app = MagicMock()
    mock_app.initiate_device_flow.return_value = {
        "user_code": "ABCD-1234",
        "verification_uri": "https://login.microsoft.com/device",
        "message": (
            "To sign in, open https://login.microsoft.com/device and enter ABCD-1234"
        ),
    }
    mock_app.acquire_token_by_device_flow.return_value = {
        "access_token": "mock_device_access_token"
    }

    with patch("msal.PublicClientApplication", return_value=mock_app):
        token = run_device_code_flow(
            client_id="test_client_id",
            authority="https://login.microsoftonline.com/tenant_id",
            scope="api://api_client_id/access_as_user",
        )
        assert token == "mock_device_access_token"


def test_run_device_code_flow_initiate_failure_exits():
    """Failure to initiate device code flow exits with status 1."""
    mock_app = MagicMock()
    mock_app.initiate_device_flow.return_value = {
        "error": "invalid_client",
        "error_description": "Client does not exist",
    }

    with patch("msal.PublicClientApplication", return_value=mock_app):
        with pytest.raises(SystemExit) as exc_info:
            run_device_code_flow(
                client_id="bad_client_id",
                authority="https://login.microsoftonline.com/tenant_id",
                scope="api://api_client_id/access_as_user",
            )
        assert exc_info.value.code == 1


def test_main_with_token_argument(capsys):
    """Passing --token runs validation & OBO routine and prints OID and group."""
    mock_settings = Settings(
        TENANT_ID="00000000-0000-0000-0000-000000000001",
        API_CLIENT_ID="00000000-0000-0000-0000-000000000002",
        LUKE_OID="11111111-1111-1111-1111-111111111111",
        TEAM_A_GROUP_ID="22222222-2222-2222-2222-222222222222",
    )
    mock_identity = UserIdentity(
        oid="11111111-1111-1111-1111-111111111111",
        tenant_id="00000000-0000-0000-0000-000000000001",
        groups=["22222222-2222-2222-2222-222222222222"],
        group_details=[
            GroupInfo(
                id="22222222-2222-2222-2222-222222222222",
                display_name="team-a",
            )
        ],
        upn="alice@testtenant.onmicrosoft.com",
        name="Alice Tester",
    )

    test_args = ["smoke_obo_device_code.py", "--token", "mock_preacquired_token"]
    with (
        patch("sys.argv", test_args),
        patch(
            "scripts.smoke_obo_device_code.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "scripts.smoke_obo_device_code.authenticate_and_resolve",
            return_value=mock_identity,
        ),
    ):
        main()

    captured = capsys.readouterr()
    assert "User OID:        11111111-1111-1111-1111-111111111111" in captured.out
    assert "22222222-2222-2222-2222-222222222222 (team-a)" in captured.out
    assert "MATCH" in captured.out
