"""
Centralized application configuration.
Loads from environment variables / .env file using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # ---- Groq ----
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ---- JWT ----
    jwt_secret_key: str = "insecure-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ---- Database ----
    database_url: str = f"sqlite:///{BASE_DIR}/database/quizify.db"

    # ---- Vector store ----
    chroma_persist_dir: str = str(BASE_DIR / "vectorstore" / "chroma_data")

    # ---- API ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"

    # ---- App ----
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
