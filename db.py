"""PostgreSQL data access layer."""
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID

import psycopg2
import psycopg2.extras

from .config import config


@contextmanager
def get_conn() -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(config.pg_dsn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(schema_path: str = "sql/schema.sql") -> None:
    """Apply DDL."""
    with open(schema_path, "r", encoding="utf-8") as f:
        ddl = f.read()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(ddl)


# ----------------------------------------------------------------
# documents
# ----------------------------------------------------------------
def upsert_document(
    *,
    source_type: str,
    source_system: str | None,
    external_id: str | None,
    title: str,
    file_path: str,
    content_hash: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[UUID, str]:
    """
    Insert or update a document. Returns (id, action) where action is
    'created' | 'updated' | 'unchanged'.
    """
    metadata = metadata or {}
    with get_conn() as conn, conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    ) as cur:
        # 既存チェック
        cur.execute(
            """
            SELECT id, content_hash FROM documents
            WHERE source_system = %s AND external_id = %s
            """,
            (source_system, external_id),
        )
        existing = cur.fetchone()

        if existing is None:
            cur.execute(
                """
                INSERT INTO documents
                  (source_type, source_system, external_id, title,
                   file_path, content_hash, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    source_type,
                    source_system,
                    external_id,
                    title,
                    file_path,
                    content_hash,
                    json.dumps(metadata),
                ),
            )
            return cur.fetchone()["id"], "created"

        if existing["content_hash"] == content_hash:
            return existing["id"], "unchanged"

        cur.execute(
            """
            UPDATE documents
               SET title = %s,
                   file_path = %s,
                   content_hash = %s,
                   metadata = %s::jsonb,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (
                title,
                file_path,
                content_hash,
                json.dumps(metadata),
                existing["id"],
            ),
        )
        return existing["id"], "updated"


def delete_chunks(document_id: UUID) -> list[str]:
    """Delete all chunks of a document. Returns deleted vector_ids for ChromaDB cleanup."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT vector_id FROM chunks WHERE document_id = %s",
            (str(document_id),),
        )
        vector_ids = [row[0] for row in cur.fetchall() if row[0]]
        cur.execute("DELETE FROM chunks WHERE document_id = %s", (str(document_id),))
        return vector_ids


def insert_chunks(
    document_id: UUID,
    chunks: list[dict[str, Any]],
) -> None:
    """chunks: [{chunk_index, content, vector_id, token_count}, ...]"""
    with get_conn() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO chunks
              (document_id, chunk_index, content, vector_id, token_count)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (
                    str(document_id),
                    c["chunk_index"],
                    c["content"],
                    c["vector_id"],
                    c.get("token_count"),
                )
                for c in chunks
            ],
        )


# ----------------------------------------------------------------
# tickets
# ----------------------------------------------------------------
def upsert_ticket(
    *,
    document_id: UUID,
    status: str | None,
    severity: str | None,
    affected_system: str | None,
    resolved_at: str | None,
    resolution: str | None,
) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tickets
              (document_id, status, severity, affected_system, resolved_at, resolution)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_id) DO UPDATE SET
              status = EXCLUDED.status,
              severity = EXCLUDED.severity,
              affected_system = EXCLUDED.affected_system,
              resolved_at = EXCLUDED.resolved_at,
              resolution = EXCLUDED.resolution
            """,
            (
                str(document_id),
                status,
                severity,
                affected_system,
                resolved_at,
                resolution,
            ),
        )


# ----------------------------------------------------------------
# ingestion log
# ----------------------------------------------------------------
def log_ingestion(
    document_id: UUID | None,
    action: str,
    message: str = "",
) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_log (document_id, action, message)
            VALUES (%s, %s, %s)
            """,
            (str(document_id) if document_id else None, action, message),
        )


# ----------------------------------------------------------------
# 検索系(後段のRAGから利用)
# ----------------------------------------------------------------
def fetch_documents_by_ids(ids: list[UUID]) -> list[dict[str, Any]]:
    if not ids:
        return []
    with get_conn() as conn, conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    ) as cur:
        cur.execute(
            """
            SELECT d.*, t.status, t.severity, t.affected_system,
                   t.resolved_at, t.resolution
              FROM documents d
              LEFT JOIN tickets t ON t.document_id = d.id
             WHERE d.id = ANY(%s::uuid[])
            """,
            ([str(i) for i in ids],),
        )
        return [dict(r) for r in cur.fetchall()]
