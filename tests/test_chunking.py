"""chunking モジュールのテスト。"""
from src.chunking import chunk_procedure, chunk_ticket, chunk_generic, chunk_by_source_type


def test_chunk_procedure_basic():
    """手順書のチャンク分割が正しく行われること。"""
    text = """# 手順書タイトル

## 概要
これは概要です。

## 手順
### Step 1
手順1の内容

### Step 2
手順2の内容
"""
    chunks = chunk_procedure(text)
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_ticket_small():
    """小さいチケットは1チャンクになること。"""
    text = "チケット内容: Podが落ちた"
    chunks = chunk_ticket(text)
    assert len(chunks) == 1


def test_chunk_generic():
    """汎用チャンク分割が動作すること。"""
    text = "あ" * 2000
    chunks = chunk_generic(text)
    assert len(chunks) > 1


def test_chunk_by_source_type_wiki():
    """source_type=wikiでchunk_procedureが使われること。"""
    text = "# Title\n\nContent"
    chunks = chunk_by_source_type("wiki", text)
    assert len(chunks) > 0


def test_chunk_by_source_type_issue():
    """source_type=issueでchunk_ticketが使われること。"""
    text = "Short ticket"
    chunks = chunk_by_source_type("issue", text)
    assert len(chunks) == 1


def test_chunk_by_source_type_unknown():
    """未知のsource_typeでchunk_genericが使われること。"""
    text = "Some content"
    chunks = chunk_by_source_type("unknown", text)
    assert len(chunks) > 0
