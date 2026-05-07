from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Veri katmanı
    database_url: str = "postgresql://repoarkeolog:repoarkeolog@localhost:5432/repoarkeolog"
    redis_url: str = "redis://localhost:6379/0"
    # Qdrant boş bırakılırsa embedding adımı sessizce atlanır.
    qdrant_url: str = ""

    # LLM anahtarları
    gemini_api_key: str = ""
    groq_api_key: str = ""
    cerebras_api_key: str = ""

    # CORS — virgülle ayrılmış origin listesi.
    # Örn: "https://app.com,https://staging.app.com"
    # "*" yalnız geliştirme için.
    cors_origins: str = "*"

    # Repo constraints
    max_repo_size_mb: int = 2048
    max_clone_depth: int = 50

    # LLM rate limit thresholds (80% of free tier)
    gemini_rpm_threshold: int = 12
    gemini_daily_req_threshold: int = 1200
    groq_rpm_threshold: int = 25

    admin_webhook_url: str = ""  # Discord/Slack webhook for usage alerts

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
