from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://repoarkeolog:repoarkeolog@localhost:5432/repoarkeolog"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    gemini_api_key: str = ""
    groq_api_key: str = ""
    cerebras_api_key: str = ""

    # Repo constraints
    max_repo_size_mb: int = 500
    max_clone_depth: int = 200

    # LLM rate limit thresholds (80% of free tier)
    gemini_rpm_threshold: int = 12
    gemini_daily_req_threshold: int = 1200
    groq_rpm_threshold: int = 25

    admin_webhook_url: str = ""  # Discord/Slack webhook for usage alerts


settings = Settings()
