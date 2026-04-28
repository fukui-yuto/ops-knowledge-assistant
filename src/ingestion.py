"""Ingestion pipeline.

Flow:
  raw file
    -> save to storage (LocalStorage)
    -> hash check (skip if unchanged)
    -> upsert documents
    -> chunk
    -> embed
    -> insert chunks (Postgres) + add to ChromaDB
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from . import db
from .chunking import chunk_by_source_type
from .config import config
from .embedding import create_embedder
from .storage import LocalStorage
from .vector_store import VectorStore


class IngestionPipeline:
    def __init__(self):
        self.storage = LocalStorage(config.raw_storage_path)
        self.embedder = create_embedder()
        self.vstore = VectorStore()

    def ingest_file(
        self,
        *,
        src_path: str | Path,
        source_type: str,
        source_system: str,
        external_id: str,
        title: str,
        metadata: dict[str, Any] | None = None,
        ticket_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        単一ファイルを取り込む。
        ticket_fields: source_type='issue' の場合のみ
        """
        src = Path(src_path)
        text = src.read_text(encoding="utf-8")
        content_hash = LocalStorage.hash_text(text)

        # 1. 原本をstorageへ
        dest_relpath = f"{source_type}/{external_id}{src.suffix}"
        self.storage.save(src, dest_relpath)

        # 2. メタDBへupsert
        doc_id, action = db.upsert_document(
            source_type=source_type,
            source_system=source_system,
            external_id=external_id,
            title=title,
            file_path=dest_relpath,
            content_hash=content_hash,
            metadata=metadata or {},
        )

        if action == "unchanged":
            db.log_ingestion(doc_id, "skip", "content_hash unchanged")
            return {"document_id": doc_id, "action": "skip", "chunks": 0}

        # 3. updated の場合は既存チャンクを削除(Chroma側も)
        if action == "updated":
            old_vec_ids = db.delete_chunks(doc_id)
            self.vstore.delete(source_type, old_vec_ids)

        # 4. ticketフィールドの保存
        if source_type == "issue" and ticket_fields:
            db.upsert_ticket(document_id=doc_id, **ticket_fields)

        # 5. チャンク分割
        chunks = chunk_by_source_type(source_type, text)
        if not chunks:
            db.log_ingestion(doc_id, "error", "no chunks generated")
            return {"document_id": doc_id, "action": "error", "chunks": 0}

        # 6. Embedding
        embeddings = self.embedder.embed(chunks)

        # 7. ベクトルID = UUID。PostgresとChromaで同じIDを共有
        vector_ids = [str(uuid.uuid4()) for _ in chunks]

        # 8. Postgresにchunks挿入
        db.insert_chunks(
            doc_id,
            [
                {
                    "chunk_index": i,
                    "content": c,
                    "vector_id": vid,
                    "token_count": len(c) // 4,  # 概算
                }
                for i, (c, vid) in enumerate(zip(chunks, vector_ids))
            ],
        )

        # 9. ChromaDBへ追加。metadataはフィルタに使う最小限
        chroma_metadatas = [
            {
                "document_id": str(doc_id),
                "source_type": source_type,
                "source_system": source_system,
                "chunk_index": i,
                **{k: v for k, v in (metadata or {}).items() if isinstance(v, (str, int, float, bool))},
            }
            for i in range(len(chunks))
        ]
        self.vstore.add(
            source_type=source_type,
            ids=vector_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=chroma_metadatas,
        )

        db.log_ingestion(doc_id, action, f"{len(chunks)} chunks")
        return {"document_id": doc_id, "action": action, "chunks": len(chunks)}
