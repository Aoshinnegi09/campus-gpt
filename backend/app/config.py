from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CampusGPT API"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 10
    chunk_size_words: int = 140
    chunk_overlap_words: int = 20
    retrieval_k: int = 5
    refusal_threshold: float = 0.12
    index_path: Path = Path(__file__).resolve().parents[1] / "storage" / "index.json"

    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CAMPUSGPT_", extra="ignore")

    @property
    def parsed_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
