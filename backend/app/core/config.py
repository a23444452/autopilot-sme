"""Application configuration using Pydantic BaseSettings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    PROJECT_NAME: str = "AutoPilot SME"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # --- PostgreSQL ---
    POSTGRES_USER: str = "autopilot"
    POSTGRES_PASSWORD: str = "autopilot_dev"
    POSTGRES_DB: str = "autopilot_sme"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://autopilot:autopilot_dev@localhost:5432/autopilot_sme"

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Qdrant ---
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

    # --- LLM API Keys ---
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # --- Production Schedule ---
    WORK_START_HOUR: int = 8
    WORK_END_HOUR: int = 17
    MAX_OVERTIME_HOURS: int = 3

    # --- Authentication ---
    API_KEY: str = ""
    API_KEY_HEADER: str = "X-API-Key"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
