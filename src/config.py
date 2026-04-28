"""設定管理。全て環境変数ベース。"""
import os
from dataclasses import dataclass


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

    # Storage
    raw_storage_path: str = os.getenv("RAW_STORAGE_PATH", "./data/raw")
    knowledge_path: str = os.getenv("KNOWLEDGE_PATH", "./data/knowledge")

    # Embedding
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")

    # Generation
    generation_model: str = os.getenv("GENERATION_MODEL", "gemini-2.5-flash-lite")

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    # Templates
    templates_path: str = os.getenv("TEMPLATES_PATH", "./data/templates")

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


config = Config()
