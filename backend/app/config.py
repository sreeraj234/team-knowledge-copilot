from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    entra_base_url: str = Field(
        default="https://login.microsoftonline.com", alias="ENTRA_BASE_URL"
    )
    tenant_id: str = Field(default="", alias="TENANT_ID")
    api_client_id: str = Field(default="", alias="API_CLIENT_ID")
    api_client_secret: str = Field(default="", alias="API_CLIENT_SECRET")
    spa_client_id: str = Field(default="", alias="SPA_CLIENT_ID")
    test_client_id: str = Field(default="", alias="TEST_CLIENT_ID")
    luke_oid: str = Field(default="", alias="LUKE_OID")
    leia_oid: str = Field(default="", alias="LEIA_OID")
    team_a_group_id: str = Field(default="", alias="TEAM_A_GROUP_ID")
    team_b_group_id: str = Field(default="", alias="TEAM_B_GROUP_ID")
    database_url: str = Field(default="", alias="DATABASE_URL")

    @property
    def authority(self) -> str:
        return f"{self.entra_base_url.rstrip('/')}/{self.tenant_id}"

    @property
    def issuer(self) -> str:
        return f"{self.authority}/v2.0"

    @property
    def jwks_uri(self) -> str:
        return f"{self.authority}/discovery/v2.0/keys"

    @property
    def api_scope(self) -> str:
        client_id = self.api_client_id.removeprefix("api://")
        return f"api://{client_id}/access_as_user"

    @property
    def allowed_audiences(self) -> list[str]:
        client_id = self.api_client_id.removeprefix("api://")
        return [client_id, f"api://{client_id}"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
