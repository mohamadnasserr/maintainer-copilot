from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    vault_addr: str = "http://localhost:8200"
    vault_root_token: str = "dev-root-token"
    vault_secret_path: str = "secret/data/maintainers-copilot"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_bucket: str = "maintainers-copilot"
    pandas_repo: str = "pandas-dev/pandas"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

