"""Embedding generation. Uses Google text-embedding-004 by default."""
from __future__ import annotations

from typing import Protocol

import google.generativeai as genai

from .config import config


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbedder:
    def __init__(self):
        if not config.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        genai.configure(api_key=config.google_api_key)
        self.model = config.embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        # text-embedding-004 はバッチ可、ただし上限あり。安全側で1件ずつ。
        results: list[list[float]] = []
        for t in texts:
            r = genai.embed_content(
                model=self.model,
                content=t,
                task_type="retrieval_document",
            )
            results.append(r["embedding"])
        return results

    def embed_query(self, text: str) -> list[float]:
        r = genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_query",
        )
        return r["embedding"]
