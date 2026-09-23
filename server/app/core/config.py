"""Configuración global del servidor."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CREDITS_PER_TASK: float = 1.0

    # Copernicus Data Space Ecosystem
    CDSE_USERNAME: str = ""
    CDSE_PASSWORD: str = ""
    CDSE_TOKEN_URL: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    CDSE_CLIENT_ID: str = "cdse-public"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
