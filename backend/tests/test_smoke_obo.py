import sys
from pathlib import Path
from unittest.mock import patch

from app.auth import GroupInfo, UserIdentity
from app.config import Settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.smoke_obo_device_code import main, run_device_code_flow  # noqa: E402


def test_device_code_flow_requests_api_scope():
    mock_app = patch("scripts.smoke_obo_device_code.msal.PublicClientApplication")
    with mock_app as app_constructor:
        app = app_constructor.return_value
        app.initiate_device_flow.return_value = {
            "user_code": "ABCD",
            "message": "Complete sign-in",
        }
        app.acquire_token_by_device_flow.return_value = {"access_token": "user-token"}

        token = run_device_code_flow(
            "public-client",
            "https://login.microsoftonline.com/tenant",
            "api://api-client/access_as_user",
        )

    assert token == "user-token"
    app.initiate_device_flow.assert_called_once_with(
        scopes=["api://api-client/access_as_user"]
    )


def test_main_with_token_argument_uses_patched_settings(capsys):
    settings = Settings(
        TENANT_ID="tenant",
        API_CLIENT_ID="api-client",
        LUKE_OID="user-oid",
        TEAM_A_GROUP_ID="team-a-id",
    )
    identity = UserIdentity(
        oid="user-oid",
        tenant_id="tenant",
        groups=["team-a-id"],
        group_details=[GroupInfo(id="team-a-id", display_name="team-a")],
    )
    with (
        patch("scripts.smoke_obo_device_code.get_settings", return_value=settings),
        patch(
            "scripts.smoke_obo_device_code.authenticate_and_resolve",
            return_value=identity,
        ) as authenticate,
    ):
        main(["--token", "user-token"])

    output = capsys.readouterr().out
    authenticate.assert_called_once_with("user-token", settings=settings)
    assert "User OID: user-oid" in output
    assert "team-a-id" in output
