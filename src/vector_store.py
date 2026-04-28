"""ChromaDB wrapper. Manages multiple collections by source_type."""
from __future__ import annotations

from typing import Any

import chromadb
from chromadb.config import Settings

from .config import config


# 用途別Collection
COLLECTIONS = {
    "wiki": "wikis",
    "issue": "issues",
}


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=config.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collections: dict[str, Any] = {}

    def _collection(self, source_type: str):
        name = COLLECTIONS.get(source_type, "default")
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def add(
        self,
        source_type: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        self._collection(source_type).add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def delete(self, source_type: str, ids: list[str]) -> None:
        if not ids:
            return
        self._collection(source_type).delete(ids=ids)

    def query(
        self,
        source_type: str,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._collection(source_type).query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
