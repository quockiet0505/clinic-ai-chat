from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "llama3.2:3b"
    CLINIC_BACKEND_URL: str = "http://localhost:8080"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 500
    CORS_ORIGINS: str = "*"

    # Light RAG: tra cứu FAQ tĩnh từ thư mục knowledge/
    RAG_ENABLED: bool = True
    RAG_TOP_K: int = 3
    RAG_MIN_SCORE: float = 0.15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
