from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    MAX_INPUT_CHARS: int = 50000
    MAX_LLM_CALLS_PER_SESSION: int = 30
    SESSION_TTL_HOURS: int = 2


settings = Settings()
