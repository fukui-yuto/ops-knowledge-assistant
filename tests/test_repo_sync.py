"""repo_sync モジュールのテスト。"""
from pathlib import Path
from unittest.mock import patch

import pytest

from src.repo_sync import (
    _get_repo_url_with_token,
    load_repos_config,
    save_repos_config,
    sync_repo_files,
)


def test_get_repo_url_with_token_no_token():
    """トークンなしの場合、URLがそのまま返ること。"""
    url = "https://github.com/org/repo.git"
    assert _get_repo_url_with_token(url, None) == url


def test_get_repo_url_with_token_env_not_set():
    """環境変数が未設定の場合、URLがそのまま返ること。"""
    url = "https://github.com/org/repo.git"
    with patch.dict("os.environ", {}, clear=True):
        assert _get_repo_url_with_token(url, "MISSING_TOKEN") == url


def test_get_repo_url_with_token_success():
    """トークンがURLに埋め込まれること。"""
    url = "https://github.com/org/repo.git"
    with patch.dict("os.environ", {"MY_TOKEN": "ghp_abc123"}):
        result = _get_repo_url_with_token(url, "MY_TOKEN")
        assert result == "https://ghp_abc123@github.com/org/repo.git"


def test_save_and_load_repos_config(tmp_path):
    """repos.yaml の保存・読み込みが正しく動作すること。"""
    config_path = tmp_path / "repos.yaml"
    repos = [
        {"name": "team-a", "url": "https://github.com/org/team-a.git", "branch": "main", "paths": {"wiki": "docs"}},
    ]

    with patch("src.repo_sync.config") as mock_config:
        mock_config.repos_config_path = str(config_path)
        save_repos_config(repos)
        loaded = load_repos_config()

    assert len(loaded) == 1
    assert loaded[0]["name"] == "team-a"
    assert loaded[0]["paths"]["wiki"] == "docs"


def test_load_repos_config_missing_file(tmp_path):
    """設定ファイルがない場合は空リストが返ること。"""
    with patch("src.repo_sync.config") as mock_config:
        mock_config.repos_config_path = str(tmp_path / "nonexistent.yaml")
        result = load_repos_config()
    assert result == []


def test_sync_repo_files(tmp_path):
    """リポジトリファイルがknowledge/に正しくコピーされること。"""
    # リポジトリのディレクトリ構造を模擬
    repos_dir = tmp_path / "repos" / "team-a"
    wiki_src = repos_dir / "docs" / "procedures"
    wiki_src.mkdir(parents=True)
    (wiki_src / "setup.md").write_text("# Setup Guide", encoding="utf-8")
    (wiki_src / "backup.md").write_text("# Backup Guide", encoding="utf-8")

    issue_src = repos_dir / "docs" / "incidents"
    issue_src.mkdir(parents=True)
    (issue_src / "ISS-001.md").write_text("# Incident 001", encoding="utf-8")

    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    repo_config = {
        "name": "team-a",
        "paths": {
            "wiki": "docs/procedures",
            "issue": "docs/incidents",
        },
    }

    with patch("src.repo_sync.config") as mock_config:
        mock_config.repos_data_path = str(tmp_path / "repos")
        mock_config.knowledge_path = str(knowledge_dir)
        stats = sync_repo_files(repo_config)

    assert stats["copied"] == 3
    assert (knowledge_dir / "wiki" / "team-a" / "setup.md").exists()
    assert (knowledge_dir / "wiki" / "team-a" / "backup.md").exists()
    assert (knowledge_dir / "issue" / "team-a" / "ISS-001.md").exists()


def test_sync_repo_files_removes_deleted(tmp_path):
    """リポジトリから削除されたファイルがknowledge/からも削除されること。"""
    repos_dir = tmp_path / "repos" / "team-a"
    wiki_src = repos_dir / "docs"
    wiki_src.mkdir(parents=True)
    (wiki_src / "remaining.md").write_text("# Remaining", encoding="utf-8")

    knowledge_dir = tmp_path / "knowledge"
    dst_dir = knowledge_dir / "wiki" / "team-a"
    dst_dir.mkdir(parents=True)
    (dst_dir / "remaining.md").write_text("# Remaining", encoding="utf-8")
    (dst_dir / "deleted.md").write_text("# Deleted", encoding="utf-8")

    repo_config = {
        "name": "team-a",
        "paths": {"wiki": "docs"},
    }

    with patch("src.repo_sync.config") as mock_config:
        mock_config.repos_data_path = str(tmp_path / "repos")
        mock_config.knowledge_path = str(knowledge_dir)
        stats = sync_repo_files(repo_config)

    assert stats["removed"] == 1
    assert not (dst_dir / "deleted.md").exists()
    assert (dst_dir / "remaining.md").exists()


def test_sync_repo_files_skips_unchanged(tmp_path):
    """内容が同じファイルはコピーをスキップすること。"""
    repos_dir = tmp_path / "repos" / "team-a"
    wiki_src = repos_dir / "docs"
    wiki_src.mkdir(parents=True)
    (wiki_src / "same.md").write_text("# Same Content", encoding="utf-8")

    knowledge_dir = tmp_path / "knowledge"
    dst_dir = knowledge_dir / "wiki" / "team-a"
    dst_dir.mkdir(parents=True)
    (dst_dir / "same.md").write_text("# Same Content", encoding="utf-8")

    repo_config = {
        "name": "team-a",
        "paths": {"wiki": "docs"},
    }

    with patch("src.repo_sync.config") as mock_config:
        mock_config.repos_data_path = str(tmp_path / "repos")
        mock_config.knowledge_path = str(knowledge_dir)
        stats = sync_repo_files(repo_config)

    assert stats["copied"] == 0
