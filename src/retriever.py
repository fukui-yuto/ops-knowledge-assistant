"""Retrieval layer: search related knowledge from ChromaDB."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from . import db
from .config import config
from .embedding import create_embedder
from .vector_store import VectorStore


class Retriever:
    def __init__(self):
        self.embedder = create_embedder()
        self.vstore = VectorStore()

    def search(
        self,
        query: str,
        source_type: str = "wiki",
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        クエリに関連するナレッジを検索する。
        source_type で検索対象コレクションを指定する。
        Returns: [{document_id, title, chunk_content, score, ...}, ...]
        """
        query_embedding = self.embedder.embed_query(query)
        results = self.vstore.query(
            source_type=source_type,
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        # ChromaDB結果を整形
        hits = []
        seen_doc_ids: set[str] = set()
        for i, vid in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            doc_id = meta.get("document_id", "")
            distance = results["distances"][0][i] if results.get("distances") else None
            hits.append({
                "vector_id": vid,
                "document_id": doc_id,
                "chunk_content": results["documents"][0][i] if results["documents"] else "",
                "chunk_index": meta.get("chunk_index", 0),
                "distance": distance,
            })
            seen_doc_ids.add(doc_id)

        # ドキュメントメタ情報を取得
        doc_ids = [UUID(d) for d in seen_doc_ids if d]
        doc_map = {}
        if doc_ids:
            docs = db.fetch_documents_by_ids(doc_ids)
            doc_map = {str(d["id"]): d for d in docs}

        # メタ情報をマージ
        for hit in hits:
            doc_info = doc_map.get(hit["document_id"], {})
            hit["title"] = doc_info.get("title", "")
            hit["source_system"] = doc_info.get("source_system", "")
            hit["external_id"] = doc_info.get("external_id", "")

        return hits

    def search_wiki(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """wiki コレクションを検索する。"""
        return self.search(query, source_type="wiki", n_results=n_results, where=where)

    def get_full_document_text(self, document_id: str) -> str:
        """ドキュメントの全チャンクを結合して全文を返す。"""
        with db.get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT content FROM chunks
                WHERE document_id = %s
                ORDER BY chunk_index
                """,
                (document_id,),
            )
            rows = cur.fetchall()
        return "\n\n".join(row[0] for row in rows)

    def get_related_full_procedures(
        self,
        query: str,
        max_docs: int = 3,
    ) -> list[dict[str, Any]]:
        """
        クエリに関連する過去手順をドキュメント単位で取得する。
        チャンク検索→ドキュメントID特定→全文取得。
        """
        hits = self.search_wiki(query, n_results=max_docs * 2)

        # ドキュメント単位で重複排除
        seen: set[str] = set()
        docs: list[dict[str, Any]] = []
        for hit in hits:
            doc_id = hit["document_id"]
            if doc_id in seen or not doc_id:
                continue
            seen.add(doc_id)
            full_text = self.get_full_document_text(doc_id)
            docs.append({
                "document_id": doc_id,
                "title": hit["title"],
                "source_system": hit["source_system"],
                "external_id": hit["external_id"],
                "full_text": full_text,
            })
            if len(docs) >= max_docs:
                break

        return docs
