"""Configuration management."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    # PostgreSQL
    pg_host: str = os.getenv("PG_HOST", "localhost")
    pg_port: int = int(os.getenv("PG_PORT", "5432"))
    pg_db: str = os.getenv("PG_DB", "log_assistant")
    pg_user: str = os.getenv("PG_USER", "postgres")
    pg_password: str = os.getenv("PG_PASSWORD", "postgres")

    # ChromaDB
    chroma_path: str = os.getenv("CHROMA_PATH", "./data/chroma")

    # Storage (raw files)
    raw_storage_path: str = os.getenv("RAW_STORAGE_PATH", "./data/raw")

    # Embedding
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


config = Config()
