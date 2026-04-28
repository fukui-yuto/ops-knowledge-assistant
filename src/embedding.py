"""Embedding生成。LLM_PROVIDERに応じてGeminiまたはOpenAIを使用する。"""
from __future__ import annotations

from typing import Protocol

from .config import config


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class GeminiEmbedder:
    def __init__(self):
        if not config.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        from google import genai
        self.client = genai.Client(api_key=config.google_api_key)
        self.model = config.embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        from google.genai import types
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
        from google.genai import types
        r = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return list(r.embeddings[0].values)


class OpenAIEmbedder:
    def __init__(self):
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import OpenAI
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = config.openai_embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for t in texts:
            r = self.client.embeddings.create(model=self.model, input=t)
            results.append(r.data[0].embedding)
        return results

    def embed_query(self, text: str) -> list[float]:
        r = self.client.embeddings.create(model=self.model, input=text)
        return r.data[0].embedding


def create_embedder() -> GeminiEmbedder | OpenAIEmbedder:
    """LLM_PROVIDERに応じたEmbedderインスタンスを返す。"""
    if config.llm_provider == "openai":
        return OpenAIEmbedder()
    return GeminiEmbedder()
