"""qa モジュールのテスト。"""
from unittest.mock import MagicMock, patch

from src.qa import KnowledgeQA, QA_SYSTEM_PROMPT


def test_qa_system_prompt_contains_rules():
    """システムプロンプトに必要なルールが含まれていること。"""
    assert "ナレッジ" in QA_SYSTEM_PROMPT
    assert "Markdown" in QA_SYSTEM_PROMPT


def test_build_prompt_with_references():
    """参照ナレッジありの場合、プロンプトにナレッジが含まれること。"""
    with patch.object(KnowledgeQA, "__init__", lambda self: None):
        qa = KnowledgeQA()
        qa.retriever = MagicMock()

        refs = [
            {"document_id": "1", "title": "バックアップ手順", "source_system": "local", "full_text": "# バックアップ\npg_dump ..."},
        ]
        prompt = qa._build_prompt("バックアップの方法は？", refs, None)

        assert "バックアップ手順" in prompt
        assert "pg_dump" in prompt
        assert "バックアップの方法は？" in prompt


def test_build_prompt_without_references():
    """参照ナレッジなしの場合、その旨がプロンプトに含まれること。"""
    with patch.object(KnowledgeQA, "__init__", lambda self: None):
        qa = KnowledgeQA()
        qa.retriever = MagicMock()

        prompt = qa._build_prompt("テスト質問", [], None)

        assert "見つかりませんでした" in prompt


def test_build_prompt_with_conversation_history():
    """会話履歴がプロンプトに含まれること。"""
    with patch.object(KnowledgeQA, "__init__", lambda self: None):
        qa = KnowledgeQA()
        qa.retriever = MagicMock()

        history = [
            {"role": "user", "content": "前の質問"},
            {"role": "assistant", "content": "前の回答"},
        ]
        prompt = qa._build_prompt("次の質問", [], history)

        assert "前の質問" in prompt
        assert "前の回答" in prompt
        assert "次の質問" in prompt


def test_search_knowledge_deduplicates():
    """検索結果がドキュメント単位で重複排除されること。"""
    with patch.object(KnowledgeQA, "__init__", lambda self: None):
        qa = KnowledgeQA()
        qa.retriever = MagicMock()

        # 同じdocument_idのチャンクが複数返る場合
        qa.retriever.search.return_value = [
            {"document_id": "doc-1", "title": "Doc1", "source_system": "local", "distance": 0.1},
            {"document_id": "doc-1", "title": "Doc1", "source_system": "local", "distance": 0.2},
            {"document_id": "doc-2", "title": "Doc2", "source_system": "local", "distance": 0.3},
        ]
        qa.retriever.get_full_document_text.return_value = "full text"

        result = qa._search_knowledge("テスト", "all", 5)

        assert len(result) == 2
        assert result[0]["document_id"] == "doc-1"
        assert result[1]["document_id"] == "doc-2"
