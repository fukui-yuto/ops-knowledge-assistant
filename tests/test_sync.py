"""sync モジュールのテスト。"""
from pathlib import Path

from sync import extract_title_from_md, scan_knowledge_dir


def test_extract_title_from_md_with_heading():
    """# 見出しからタイトルを抽出できること。"""
    text = "# PostgreSQL バックアップ手順\n\n## 概要\n..."
    title = extract_title_from_md(text, "backup")
    assert title == "PostgreSQL バックアップ手順"


def test_extract_title_from_md_no_heading():
    """見出しがない場合はファイル名からタイトルを生成すること。"""
    text = "This file has no heading"
    title = extract_title_from_md(text, "server_setup")
    assert title == "server setup"


def test_extract_title_from_md_h2_only():
    """## のみの場合はファイル名からタイトルを生成すること。"""
    text = "## これはh2見出し\n内容"
    title = extract_title_from_md(text, "my_file")
    assert title == "my file"


def test_scan_knowledge_dir_empty(tmp_path):
    """空のディレクトリでは空リストが返ること。"""
    files = scan_knowledge_dir(tmp_path)
    assert files == []


def test_scan_knowledge_dir_nonexistent(tmp_path):
    """存在しないディレクトリでは空リストが返ること。"""
    files = scan_knowledge_dir(tmp_path / "nonexistent")
    assert files == []


def test_scan_knowledge_dir_with_files(tmp_path):
    """ディレクトリ構造からメタデータが正しく抽出されること。"""
    # テスト用のディレクトリ構造を作成
    proc_dir = tmp_path / "procedure" / "confluence"
    proc_dir.mkdir(parents=True)
    (proc_dir / "server_setup.md").write_text(
        "# サーバー構築手順\n\n## 概要\nサーバーを構築する手順",
        encoding="utf-8",
    )

    ticket_dir = tmp_path / "ticket" / "jira"
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "JIRA-123.md").write_text(
        "# Pod CrashLoopBackOff\n\nPodが落ちた",
        encoding="utf-8",
    )

    files = scan_knowledge_dir(tmp_path)
    assert len(files) == 2

    proc_file = next(f for f in files if f["source_type"] == "procedure")
    assert proc_file["source_system"] == "confluence"
    assert proc_file["external_id"] == "server_setup"
    assert proc_file["title"] == "サーバー構築手順"

    ticket_file = next(f for f in files if f["source_type"] == "ticket")
    assert ticket_file["source_system"] == "jira"
    assert ticket_file["external_id"] == "JIRA-123"
    assert ticket_file["title"] == "Pod CrashLoopBackOff"


def test_scan_knowledge_dir_ignores_invalid_types(tmp_path):
    """不正なsource_typeフォルダは無視されること。"""
    invalid_dir = tmp_path / "invalid_type" / "system"
    invalid_dir.mkdir(parents=True)
    (invalid_dir / "file.md").write_text("content", encoding="utf-8")

    files = scan_knowledge_dir(tmp_path)
    assert len(files) == 0
