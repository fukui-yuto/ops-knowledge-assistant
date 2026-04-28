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
    """3階層ディレクトリ構造からメタデータが正しく抽出されること。"""
    # テスト用のディレクトリ構造を作成（3階層: source_type/source_system/file.md）
    wiki_local = tmp_path / "wiki" / "local"
    wiki_local.mkdir(parents=True)
    (wiki_local / "server_setup.md").write_text(
        "# サーバー構築手順\n\n## 概要\nサーバーを構築する手順",
        encoding="utf-8",
    )

    issue_local = tmp_path / "issue" / "local"
    issue_local.mkdir(parents=True)
    (issue_local / "JIRA-123.md").write_text(
        "# Pod CrashLoopBackOff\n\nPodが落ちた",
        encoding="utf-8",
    )

    files = scan_knowledge_dir(tmp_path)
    assert len(files) == 2

    wiki_file = next(f for f in files if f["source_type"] == "wiki")
    assert wiki_file["source_system"] == "local"
    assert wiki_file["external_id"] == "server_setup"
    assert wiki_file["title"] == "サーバー構築手順"

    issue_file = next(f for f in files if f["source_type"] == "issue")
    assert issue_file["source_system"] == "local"
    assert issue_file["external_id"] == "JIRA-123"
    assert issue_file["title"] == "Pod CrashLoopBackOff"


def test_scan_knowledge_dir_multiple_sources(tmp_path):
    """異なるsource_system（local + リポジトリ名）が共存できること。"""
    wiki_local = tmp_path / "wiki" / "local"
    wiki_local.mkdir(parents=True)
    (wiki_local / "local_doc.md").write_text("# ローカル手順", encoding="utf-8")

    wiki_repo = tmp_path / "wiki" / "team-a"
    wiki_repo.mkdir(parents=True)
    (wiki_repo / "repo_doc.md").write_text("# リポ手順", encoding="utf-8")

    files = scan_knowledge_dir(tmp_path)
    assert len(files) == 2

    local_file = next(f for f in files if f["source_system"] == "local")
    assert local_file["external_id"] == "local_doc"
    assert local_file["title"] == "ローカル手順"

    repo_file = next(f for f in files if f["source_system"] == "team-a")
    assert repo_file["external_id"] == "repo_doc"
    assert repo_file["title"] == "リポ手順"


def test_scan_knowledge_dir_ignores_invalid_types(tmp_path):
    """不正なsource_typeフォルダは無視されること。"""
    invalid_dir = tmp_path / "invalid_type" / "local"
    invalid_dir.mkdir(parents=True)
    (invalid_dir / "file.md").write_text("content", encoding="utf-8")

    files = scan_knowledge_dir(tmp_path)
    assert len(files) == 0


def test_scan_knowledge_dir_ignores_readme(tmp_path):
    """README.mdは無視されること。"""
    wiki_local = tmp_path / "wiki" / "local"
    wiki_local.mkdir(parents=True)
    (wiki_local / "README.md").write_text("# README", encoding="utf-8")
    (wiki_local / "actual_doc.md").write_text("# 実際のドキュメント", encoding="utf-8")

    files = scan_knowledge_dir(tmp_path)
    assert len(files) == 1
    assert files[0]["external_id"] == "actual_doc"


def test_scan_knowledge_dir_ignores_non_dir_source_system(tmp_path):
    """source_type直下のファイル（2階層目がディレクトリでない）は無視されること。"""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)
    # source_type直下にファイルを直置き（3階層でないため無視される）
    (wiki_dir / "orphan.md").write_text("# 孤立ファイル", encoding="utf-8")

    # 正しい3階層のファイル
    wiki_local = wiki_dir / "local"
    wiki_local.mkdir(parents=True)
    (wiki_local / "valid.md").write_text("# 有効なファイル", encoding="utf-8")

    files = scan_knowledge_dir(tmp_path)
    assert len(files) == 1
    assert files[0]["external_id"] == "valid"
