"""Raw file storage. Local FS implementation (replace with MinIO/S3 later)."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def save(self, src_path: str | Path, dest_relpath: str) -> str: ...
    def read_text(self, relpath: str) -> str: ...
    def hash_file(self, path: str | Path) -> str: ...


class LocalStorage:
    """Local filesystem storage. Files are stored under base_path."""

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, src_path: str | Path, dest_relpath: str) -> str:
        """Copy src into storage. Returns the stored relative path."""
        src = Path(src_path)
        dest = self.base_path / dest_relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return str(dest_relpath)

    def read_text(self, relpath: str) -> str:
        return (self.base_path / relpath).read_text(encoding="utf-8")

    def delete(self, relpath: str) -> bool:
        """ストレージからファイルを削除する。"""
        path = self.base_path / relpath
        if path.exists():
            path.unlink()
            return True
        return False

    @staticmethod
    def hash_file(path: str | Path) -> str:
        """SHA256 of file content. Used for change detection."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
