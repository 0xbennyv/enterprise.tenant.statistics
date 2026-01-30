# app/core/config.py

from pydantic_settings import BaseSettings

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

    class Config:
        env_file = ".env"

settings = Settings()
