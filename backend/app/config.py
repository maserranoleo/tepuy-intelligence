from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Single .env at the repo root. Resolves regardless of CWD so `uvicorn` /
# `alembic` / ad-hoc scripts all see the same config.
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str = ""
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

if not settings.database_url:
    raise RuntimeError(
        f"DATABASE_URL is empty. Copy .env.example to .env at {ROOT_ENV.parent} "
        "and fill in your Supabase connection string."
    )
