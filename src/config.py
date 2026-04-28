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

    # LLMプロバイダ選択: "gemini" または "openai"
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")

    # Gemini
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
    generation_model: str = os.getenv("GENERATION_MODEL", "gemini-2.5-flash-lite")

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_generation_model: str = os.getenv("OPENAI_GENERATION_MODEL", "gpt-4o-mini")

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

    @property
    def active_api_key(self) -> str:
        """現在のプロバイダに対応するAPIキーを返す。"""
        if self.llm_provider == "openai":
            return self.openai_api_key
        return self.google_api_key

    @property
    def active_embedding_model(self) -> str:
        """現在のプロバイダに対応するEmbeddingモデル名を返す。"""
        if self.llm_provider == "openai":
            return self.openai_embedding_model
        return self.embedding_model

    @property
    def active_generation_model(self) -> str:
        """現在のプロバイダに対応する生成モデル名を返す。"""
        if self.llm_provider == "openai":
            return self.openai_generation_model
        return self.generation_model


config = Config()
