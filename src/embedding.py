"""Embedding generation. Uses Google gemini-embedding-001 by default."""
from __future__ import annotations

from typing import Protocol

from google import genai
from google.genai import types

from .config import config


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbedder:
    def __init__(self):
        if not config.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        self.client = genai.Client(api_key=config.google_api_key)
        self.model = config.embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        # gemini-embedding-001 はバッチ可、ただし上限あり。安全側で1件ずつ。
        results: list[list[float]] = []
        for t in texts:
            r = self.client.models.embed_content(
                model=self.model,
                contents=t,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            results.append(list(r.embeddings[0].values))
        return results

    def embed_query(self, text: str) -> list[float]:
        r = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return list(r.embeddings[0].values)
