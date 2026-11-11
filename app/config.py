
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "SchoolRoute AI"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"

    DATABASE_URL: str = "sqlite:///./schoolroute.db"

    RANDOM_SEED: int = 20261022

    STARTER_STUDENTS: int = 100
    STARTER_BUSES: int = 10
    STARTER_STOPS: int = 30
    STARTER_SCHOOL_DAYS: int = 10

    FULL_STUDENTS: int = 5000
    FULL_BUSES: int = 100
    FULL_STOPS: int = 300
    FULL_SCHOOL_DAYS: int = 200

    SCHOOL_YEAR: int = 2026

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
