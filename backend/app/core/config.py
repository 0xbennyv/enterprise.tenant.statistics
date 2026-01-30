# app/core/config.py

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    ENV: str = "development"
    PORT: int = 3001
    CLIENT_ID: str
    CLIENT_SECRET: str

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # class Config:
    #     env_file = ".env"
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

settings = Settings()
