"""Configuración global del servidor."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CREDITS_PER_TASK: float = 1.0
    # Créditos extra por segundo de cómputo (tope anti-abuso)
    CREDITS_PER_COMPUTE_SEC: float = 0.1
    CREDITS_COMPUTE_CAP_SEC: float = 60.0  # máx. segundos que cuentan
      

    # Copernicus Data Space Ecosystem
    CDSE_USERNAME: str = ""
    CDSE_PASSWORD: str = ""
    CDSE_TOKEN_URL: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    CDSE_CLIENT_ID: str = "cdse-public"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
