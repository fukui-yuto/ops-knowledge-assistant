"""Retrieval layer: search related knowledge from ChromaDB.

検索改善機能:
- HyDE: 質問から仮回答を生成し、その文でベクトル検索（ENABLE_HYDE=true）
- ハイブリッド検索: ベクトル検索 + PostgreSQL キーワード検索をRRFで統合（ENABLE_HYBRID=true）
- リランキング: LLMが検索結果の関連度を再評価（ENABLE_RERANK=true）
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from . import db
from .config import config
from .embedding import create_embedder
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


def _generate_hyde_document(query: str) -> str:
    """HyDE: クエリから仮の回答文を生成する。"""
    prompt = (
        "以下の質問に対する回答を、運用手順書やナレッジ記事のスタイルで簡潔に書いてください。\n"
        "実際の正確さは不要です。検索用の文書として使うため、関連する技術用語や手順を含めてください。\n"
        f"\n質問: {query}\n\n回答:"
    )
    model = config.active_generation_model
    if config.llm_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=config.openai_api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content
    else:
        from google import genai
        client = genai.Client(api_key=config.google_api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text


def _rerank_with_llm(query: str, hits: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    """LLMベースのリランキング。検索結果を関連度で再評価する。"""
    if not hits:
        return hits

    # チャンク内容を番号付きで提示
    chunks_text = ""
    for i, hit in enumerate(hits):
        content = hit.get("chunk_content", "")[:300]
        chunks_text += f"\n[{i}] {content}\n"

    prompt = (
        "以下の検索クエリと検索結果があります。各結果の関連度を評価し、"
        "関連度の高い順に番号を JSON 配列で返してください。\n"
        "出力は JSON 配列のみ（例: [2, 0, 3, 1]）。説明は不要です。\n"
        f"\nクエリ: {query}\n\n検索結果:{chunks_text}\n\n関連度順:"
    )

    model = config.active_generation_model
    try:
        if config.llm_provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=config.openai_api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
            )
            ranking_text = response.choices[0].message.content
        else:
            from google import genai
            client = genai.Client(api_key=config.google_api_key)
            response = client.models.generate_content(model=model, contents=prompt)
            ranking_text = response.text

        # JSON配列をパース
        ranking_text = ranking_text.strip()
        # マークダウンコードブロックの除去
        if ranking_text.startswith("```"):
            ranking_text = ranking_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        ranking = json.loads(ranking_text)
        reranked = [hits[idx] for idx in ranking if 0 <= idx < len(hits)]
        return reranked[:top_n]
    except Exception:
        logger.warning("[rerank] LLMリランキング失敗、元の順序を使用")
        return hits[:top_n]


def _reciprocal_rank_fusion(
    results_list: list[list[dict[str, Any]]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion で複数の検索結果を統合する。"""
    scores: dict[str, float] = {}
    hit_map: dict[str, dict[str, Any]] = {}

    for results in results_list:
        for rank, hit in enumerate(results):
            key = hit.get("vector_id") or f"{hit.get('document_id', '')}_{hit.get('chunk_index', 0)}"
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in hit_map:
                hit_map[key] = hit

    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [hit_map[key] for key in sorted_keys]


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
        HyDE・ハイブリッド検索・リランキングが有効な場合は自動的に適用される。
        Returns: [{document_id, title, chunk_content, score, ...}, ...]
        """
        # HyDE: 仮回答を生成して検索クエリに使用
        search_query = query
        if config.enable_hyde:
            try:
                hyde_doc = _generate_hyde_document(query)
                search_query = hyde_doc
                logger.info("[hyde] 仮回答を生成して検索に使用")
            except Exception:
                logger.warning("[hyde] 仮回答生成失敗、元のクエリを使用")

        # ベクトル検索
        fetch_n = n_results * 3 if (config.enable_rerank or config.enable_hybrid) else n_results
        vector_hits = self._vector_search(search_query, source_type, fetch_n, where)

        # ハイブリッド検索: キーワード検索とRRFで統合
        if config.enable_hybrid:
            keyword_hits = self._keyword_search(query, source_type, fetch_n)
            hits = _reciprocal_rank_fusion([vector_hits, keyword_hits])
            logger.info(f"[hybrid] ベクトル {len(vector_hits)}件 + キーワード {len(keyword_hits)}件 → RRF {len(hits)}件")
        else:
            hits = vector_hits

        # リランキング
        if config.enable_rerank and hits:
            hits = _rerank_with_llm(query, hits, n_results)
            logger.info(f"[rerank] LLMリランキング適用 → {len(hits)}件")
        else:
            hits = hits[:n_results]

        # ドキュメントメタ情報をマージ
        return self._enrich_with_doc_meta(hits)

    def _vector_search(
        self,
        query: str,
        source_type: str,
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """ChromaDBベクトル検索の内部実装。"""
        query_embedding = self.embedder.embed_query(query)
        results = self.vstore.query(
            source_type=source_type,
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        hits = []
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

        return hits

    def _keyword_search(
        self,
        query: str,
        source_type: str,
        n_results: int,
    ) -> list[dict[str, Any]]:
        """PostgreSQLキーワード検索の内部実装。"""
        try:
            rows = db.keyword_search(query, source_type=source_type, n_results=n_results)
        except Exception:
            logger.warning("[hybrid] キーワード検索失敗")
            return []

        return [
            {
                "vector_id": row.get("vector_id", ""),
                "document_id": str(row["document_id"]),
                "chunk_content": row["content"],
                "chunk_index": row["chunk_index"],
                "distance": None,
            }
            for row in rows
        ]

    def _enrich_with_doc_meta(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """検索結果にドキュメントメタ情報をマージする。"""
        seen_doc_ids: set[str] = set()
        for hit in hits:
            doc_id = hit.get("document_id", "")
            if doc_id:
                seen_doc_ids.add(doc_id)

        doc_ids = [UUID(d) for d in seen_doc_ids if d]
        doc_map = {}
        if doc_ids:
            docs = db.fetch_documents_by_ids(doc_ids)
            doc_map = {str(d["id"]): d for d in docs}

        for hit in hits:
            doc_info = doc_map.get(hit.get("document_id", ""), {})
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
