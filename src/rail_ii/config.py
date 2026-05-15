"""Application configuration loaded from environment / .env files."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global settings - values are read from env vars or a .env file."""

    model_config = {"env_prefix": "RAIL_II_", "env_file": ".env", "extra": "ignore"}

    debug: bool = False
    data_dir: str = "data"


settings = Settings()
