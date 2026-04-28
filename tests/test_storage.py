"""storage モジュールのテスト。"""
import tempfile
from pathlib import Path

from src.storage import LocalStorage


def test_hash_text():
    """同一テキストは同じハッシュになること。"""
    h1 = LocalStorage.hash_text("hello")
    h2 = LocalStorage.hash_text("hello")
    assert h1 == h2
    assert len(h1) == 64  # SHA256


def test_hash_text_different():
    """異なるテキストは異なるハッシュになること。"""
    h1 = LocalStorage.hash_text("hello")
    h2 = LocalStorage.hash_text("world")
    assert h1 != h2


def test_save_and_read(tmp_path):
    """ファイルを保存して読み込めること。"""
    storage = LocalStorage(tmp_path / "storage")

    # テスト用ファイル作成
    src = tmp_path / "test.md"
    src.write_text("# テスト手順\n\n手順内容", encoding="utf-8")

    # 保存
    relpath = storage.save(src, "procedure/test/test.md")
    assert relpath == "procedure/test/test.md"

    # 読み込み
    content = storage.read_text("procedure/test/test.md")
    assert "テスト手順" in content


def test_delete(tmp_path):
    """ファイルを削除できること。"""
    storage = LocalStorage(tmp_path / "storage")

    src = tmp_path / "test.md"
    src.write_text("content", encoding="utf-8")
    storage.save(src, "test.md")

    assert storage.delete("test.md") is True
    assert storage.delete("nonexistent.md") is False


def test_hash_file(tmp_path):
    """ファイルのハッシュが正しく計算されること。"""
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")

    h = LocalStorage.hash_file(f)
    assert len(h) == 64
    assert h == LocalStorage.hash_text("hello")
