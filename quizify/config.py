"""
Centralized application configuration.
Loads from environment variables / .env file using pydantic-settings.
"""
from pydantic import model_validator
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

    @model_validator(mode="after")
    def resolve_paths(self):
        # Resolve database_url if it's relative SQLite path
        if self.database_url.startswith("sqlite:///"):
            db_path_str = self.database_url.replace("sqlite:///", "", 1)
            db_path = Path(db_path_str)
            if not db_path.is_absolute():
                self.database_url = f"sqlite:///{ (BASE_DIR / db_path).resolve().as_posix() }"
        
        # Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
        
        # Resolve chroma_persist_dir
        chroma_path = Path(self.chroma_persist_dir)
        if not chroma_path.is_absolute():
            self.chroma_persist_dir = str((BASE_DIR / chroma_path).resolve())
            
        return self


settings = Settings()

