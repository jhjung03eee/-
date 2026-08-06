from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Elice LLM (OpenAI-compatible)
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://kia-ai.elice.io/v1", validation_alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(
        default="openai/gpt-5.6-luna", validation_alias="OPENAI_MODEL"
    )
    openai_embedding_model: str = Field(
        default="openai/text-embedding-3-small",
        validation_alias="OPENAI_EMBEDDING_MODEL",
    )
    llm_timeout_seconds: float = 90.0
    # NOTE: gpt-5.6-luna 모델은 temperature 기본값(1)만 지원
    llm_temperature: float = 1.0

    # 비즈니스 규칙
    min_project_budget: int = 1_000_000_000  # 10억
    min_preparation_days: int = 7
    urgent_threshold_days: int = 7

    # 스코어링 임계값
    strong_threshold: float = 0.75
    review_threshold: float = 0.50

    # 가중치
    weight_qualification_fit: float = 0.35
    weight_budget_fit: float = 0.20
    weight_track_record_match: float = 0.20
    weight_eval_criteria_advantage: float = 0.15
    weight_risk_penalty: float = 0.10

    # 경로
    corpus_dir: str = "./raw"
    output_dir: str = "./reports"

    # 실행
    concurrency: int = 4
    log_level: str = "INFO"

    @property
    def corpus_path(self) -> Path:
        return Path(self.corpus_dir).expanduser()

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir).expanduser()

    @property
    def live_llm(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()