from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql://moodlist:moodlist@localhost:5432/moodlist"
    redis_url: str = "redis://localhost:6379/0"
    sbert_model: str = "all-MiniLM-L6-v2"
    model_version: int = 1
    lyric_weight: float = 0.65
    genre_weight: float = 0.25
    scalar_weight: float = 0.10
    mmr_lambda: float = 0.5
    cors_origins: list[str] = ["*"]


settings = Settings()
