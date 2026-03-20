"""Configuration settings for Payment Reconciliation Agent."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Agent runtime configuration."""

    model: str = "gpt-4o"
    api_key: str | None = None
    api_base: str | None = None
    max_tokens: int = 4096

    class Config:
        env_prefix = "RECONCILIATION_AGENT_"
        env_file = ".env"
        extra = "ignore"


default_config = Config()
