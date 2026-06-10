"""Application configuration loaded from environment / .env files."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global settings - values are read from env vars or a .env file."""

    model_config = {"env_prefix": "RAIL_II_", "env_file": ".env", "extra": "ignore"}

    debug: bool = False
    data_dir: str = "data"

    # OpenAI provider settings. The API key is wrapped in SecretStr so it is
    # never printed in logs, repr() output, or stack traces.
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"


settings = Settings()
