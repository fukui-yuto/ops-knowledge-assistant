"""retriever モジュールのテスト。検索改善機能（RRF, リランキング, HyDE）を含む。"""
import json
from unittest.mock import MagicMock, patch

from src.retriever import (
    Retriever,
    _reciprocal_rank_fusion,
    _rerank_with_llm,
)


# ----------------------------------------------------------------
# RRF (Reciprocal Rank Fusion)
# ----------------------------------------------------------------
def test_rrf_single_list():
    """単一リストの場合、順序が維持されること。"""
    hits = [
        {"vector_id": "a", "document_id": "d1", "chunk_content": "aaa", "chunk_index": 0},
        {"vector_id": "b", "document_id": "d2", "chunk_content": "bbb", "chunk_index": 0},
    ]
    result = _reciprocal_rank_fusion([hits])
    assert len(result) == 2
    assert result[0]["vector_id"] == "a"
    assert result[1]["vector_id"] == "b"


def test_rrf_merges_two_lists():
    """2つのリストが統合され、両方に登場するアイテムのスコアが高くなること。"""
    list1 = [
        {"vector_id": "a", "document_id": "d1", "chunk_content": "aaa", "chunk_index": 0},
        {"vector_id": "b", "document_id": "d2", "chunk_content": "bbb", "chunk_index": 0},
    ]
    list2 = [
        {"vector_id": "b", "document_id": "d2", "chunk_content": "bbb", "chunk_index": 0},
        {"vector_id": "c", "document_id": "d3", "chunk_content": "ccc", "chunk_index": 0},
    ]
    result = _reciprocal_rank_fusion([list1, list2])

    # "b" は両方のリストに登場するのでスコアが最も高い
    assert result[0]["vector_id"] == "b"
    assert len(result) == 3


def test_rrf_empty_lists():
    """空リストの場合、空の結果を返すこと。"""
    result = _reciprocal_rank_fusion([[], []])
    assert result == []


# ----------------------------------------------------------------
# リランキング
# ----------------------------------------------------------------
@patch("src.retriever.config")
def test_rerank_with_llm_success(mock_config):
    """LLMリランキングが正常に動作すること。"""
    mock_config.llm_provider = "openai"
    mock_config.openai_api_key = "test-key"
    mock_config.active_generation_model = "gpt-4o-mini"

    hits = [
        {"chunk_content": "チャンク0"},
        {"chunk_content": "チャンク1"},
        {"chunk_content": "チャンク2"},
    ]

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "[2, 0, 1]"
        mock_client.chat.completions.create.return_value = mock_response

        result = _rerank_with_llm("テストクエリ", hits, top_n=2)

    assert len(result) == 2
    assert result[0]["chunk_content"] == "チャンク2"
    assert result[1]["chunk_content"] == "チャンク0"


@patch("src.retriever.config")
def test_rerank_with_llm_fallback_on_error(mock_config):
    """LLMリランキングが失敗した場合、元の順序を返すこと。"""
    mock_config.llm_provider = "openai"
    mock_config.openai_api_key = "test-key"
    mock_config.active_generation_model = "gpt-4o-mini"

    hits = [
        {"chunk_content": "チャンク0"},
        {"chunk_content": "チャンク1"},
        {"chunk_content": "チャンク2"},
    ]

    with patch("openai.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.side_effect = Exception("API error")
        result = _rerank_with_llm("テストクエリ", hits, top_n=2)

    assert len(result) == 2
    assert result[0]["chunk_content"] == "チャンク0"


def test_rerank_empty_hits():
    """空の検索結果の場合、空を返すこと。"""
    result = _rerank_with_llm("テスト", [], top_n=5)
    assert result == []


# ----------------------------------------------------------------
# HyDE
# ----------------------------------------------------------------
@patch("src.retriever.config")
def test_hyde_generates_document(mock_config):
    """HyDEが仮回答を生成すること。"""
    mock_config.llm_provider = "openai"
    mock_config.openai_api_key = "test-key"
    mock_config.active_generation_model = "gpt-4o-mini"

    from src.retriever import _generate_hyde_document

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "PostgreSQLのバックアップにはpg_dumpを使用します。"
        mock_client.chat.completions.create.return_value = mock_response

        result = _generate_hyde_document("バックアップ方法を教えて")

    assert "pg_dump" in result


# ----------------------------------------------------------------
# Retriever.search 統合テスト
# ----------------------------------------------------------------
@patch("src.retriever.config")
def test_search_uses_hyde_when_enabled(mock_config):
    """HyDE有効時、仮回答を使って検索すること。"""
    mock_config.enable_hyde = True
    mock_config.enable_hybrid = False
    mock_config.enable_rerank = False
    mock_config.llm_provider = "openai"
    mock_config.openai_api_key = "test-key"
    mock_config.active_generation_model = "gpt-4o-mini"

    with patch.object(Retriever, "__init__", lambda self: None):
        retriever = Retriever()
        retriever.embedder = MagicMock()
        retriever.vstore = MagicMock()

        with patch("src.retriever._generate_hyde_document", return_value="仮回答テキスト") as mock_hyde:
            retriever._vector_search = MagicMock(return_value=[])
            retriever._enrich_with_doc_meta = MagicMock(return_value=[])

            retriever.search("テスト質問", source_type="wiki", n_results=5)

            mock_hyde.assert_called_once_with("テスト質問")
            # _vector_search には仮回答が渡される
            retriever._vector_search.assert_called_once()
            call_args = retriever._vector_search.call_args
            assert call_args[0][0] == "仮回答テキスト"


@patch("src.retriever.config")
def test_search_uses_hybrid_when_enabled(mock_config):
    """ハイブリッド検索有効時、キーワード検索も実行しRRFで統合すること。"""
    mock_config.enable_hyde = False
    mock_config.enable_hybrid = True
    mock_config.enable_rerank = False

    with patch.object(Retriever, "__init__", lambda self: None):
        retriever = Retriever()
        retriever.embedder = MagicMock()
        retriever.vstore = MagicMock()

        vector_hits = [
            {"vector_id": "v1", "document_id": "d1", "chunk_content": "ベクトル結果", "chunk_index": 0, "distance": 0.1},
        ]
        keyword_hits = [
            {"vector_id": "k1", "document_id": "d2", "chunk_content": "キーワード結果", "chunk_index": 0, "distance": None},
        ]
        retriever._vector_search = MagicMock(return_value=vector_hits)
        retriever._keyword_search = MagicMock(return_value=keyword_hits)
        retriever._enrich_with_doc_meta = MagicMock(side_effect=lambda x: x)

        result = retriever.search("テスト", source_type="wiki", n_results=5)

        retriever._keyword_search.assert_called_once()
        assert len(result) == 2


@patch("src.retriever.config")
def test_search_default_no_improvements(mock_config):
    """全機能無効時、通常のベクトル検索のみ行うこと。"""
    mock_config.enable_hyde = False
    mock_config.enable_hybrid = False
    mock_config.enable_rerank = False

    with patch.object(Retriever, "__init__", lambda self: None):
        retriever = Retriever()
        retriever.embedder = MagicMock()
        retriever.vstore = MagicMock()

        vector_hits = [
            {"vector_id": "v1", "document_id": "d1", "chunk_content": "結果", "chunk_index": 0, "distance": 0.1},
        ]
        retriever._vector_search = MagicMock(return_value=vector_hits)
        retriever._enrich_with_doc_meta = MagicMock(side_effect=lambda x: x)

        result = retriever.search("テスト", source_type="wiki", n_results=5)

        assert len(result) == 1
        assert result[0]["vector_id"] == "v1"
