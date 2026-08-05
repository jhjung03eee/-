from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BIDCOM_", env_file=REPO_ROOT / ".env", extra="ignore"
    )

    openai_api_key: str = Field(
        default="", validation_alias=AliasChoices("OPENAI_API_KEY", "API_KEY")
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", validation_alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-5-nano", validation_alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", validation_alias="OPENAI_EMBEDDING_MODEL"
    )
    llm_timeout_seconds: float = 90.0
    llm_temperature: float = 0.2

    chunk_size: int = 900
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    confidence_threshold: float = 0.65
    min_citations_per_opinion: int = 1

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    corpus_dir: str = ""
    screening_concurrency: int = 4

    @property
    def live_llm(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def corpus_path(self) -> Path:
        """Real dataset when present, bundled demo corpus otherwise."""
        if self.corpus_dir:
            return Path(self.corpus_dir).expanduser()
        real = REPO_ROOT / "projects" / "raw"
        return real if real.is_dir() else DATA_DIR / "demo_corpus"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
