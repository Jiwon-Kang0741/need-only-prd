from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    LLM_PROVIDER: str = "azure_openai"
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_MODEL_NAME: str = "gpt-5.4"
    AZURE_OPENAI_API_KEY: str = ""
    CODEX_AZURE_OPENAI_ENDPOINT: str = ""
    CODEX_AZURE_OPENAI_API_VERSION: str = "2025-04-01-preview"
    CODEX_AZURE_OPENAI_MODEL_NAME: str = "gpt-5.3-codex"
    CODEX_AZURE_OPENAI_API_KEY: str = ""
    MAX_INPUT_CHARS: int = 50000
    MAX_LLM_CALLS_PER_SESSION: int = 200
    SESSION_TTL_HOURS: int = 2
    PROMPT_REFERENCE_DIR: str = "../pfy_prompt"
    CODEGEN_MAX_TOKENS: int = 16384
    DOCKER_WORKSPACE_DIR: str = "/tmp/codegen_workspaces"
    DOCKER_TIMEOUT_SECONDS: int = 300
    DOCKER_MAX_FIX_RETRIES: int = 3

    # Deploy mode: "docker" (default) or "pfy" (local PFY workspace)
    CODEGEN_DEPLOY_MODE: str = "docker"

    # PFY local workspace paths (used only when CODEGEN_DEPLOY_MODE == "pfy")
    PFY_BACKEND_DIR: str = "C:/workspace_pfy/PFY/pfy"
    PFY_FRONT_DIR: str = "C:/workspace_pfy/PFY/pfy-front"
    PFY_BACKEND_DEV_PORT: int = 8080
    PFY_FRONT_DEV_PORT: int = 3000


settings = Settings()
