from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta a backend/.env: evita que la carga dependa del cwd
# desde el que se invoque uvicorn/alembic.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str = "postgresql+psycopg://sacame:sacame@localhost:5434/sacame"
    # Sin default seguro a propósito: en producción DEBE venir de .env / secretos.
    # El valor por defecto solo sirve para desarrollo local.
    jwt_secret_key: str = "dev-secret-cambiar-en-produccion"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # Base del link que codifica el QR de cada mesa (ver Brain.md).
    frontend_base_url: str = "http://localhost:5173"


settings = Settings()
