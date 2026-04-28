"""Chunking strategies. Different per source_type."""
from __future__ import annotations

import re
from typing import Iterator

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from .config import config


def chunk_procedure(text: str) -> list[str]:
    """
    手順書: Markdown見出し単位で分割 → 大きすぎる場合のみ再分割。
    手順は文脈の連続性が重要なのでヘッダ単位を優先。
    """
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
    )
    docs = md_splitter.split_text(text)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    chunks: list[str] = []
    for d in docs:
        if len(d.page_content) <= config.chunk_size:
            chunks.append(d.page_content)
        else:
            chunks.extend(char_splitter.split_text(d.page_content))
    return chunks


def chunk_ticket(text: str) -> list[str]:
    """
    チケット: 1チケット = 1チャンクが基本。
    巨大な場合のみ意味的に分割。
    """
    if len(text) <= config.chunk_size * 2:
        return [text]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", " "],
    )
    return splitter.split_text(text)


def chunk_generic(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    return splitter.split_text(text)


def chunk_by_source_type(source_type: str, text: str) -> list[str]:
    if source_type == "procedure":
        return chunk_procedure(text)
    if source_type == "ticket":
        return chunk_ticket(text)
    return chunk_generic(text)
