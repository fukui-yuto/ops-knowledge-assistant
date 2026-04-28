"""ナレッジディレクトリのファイル監視。変更検知時に自動同期を実行する。"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import config

logger = logging.getLogger(__name__)

# 同期のデバウンス間隔（秒）。短時間に複数ファイル変更があってもまとめて1回だけ同期する。
DEBOUNCE_SECONDS = 3.0


class _KnowledgeEventHandler(FileSystemEventHandler):
    """data/knowledge/ 配下の .md ファイル変更を検知するハンドラ。"""

    def __init__(self, on_change: Callable[[], None]):
        super().__init__()
        self._on_change = on_change
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _schedule_sync(self) -> None:
        """デバウンス付きで同期をスケジュールする。"""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
        try:
            self._on_change()
        except Exception:
            logger.exception("自動同期中にエラーが発生しました")

    def _is_target(self, path: str) -> bool:
        return path.endswith(".md")

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_target(event.src_path):
            logger.info(f"[watcher] 検知: 作成 {event.src_path}")
            self._schedule_sync()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_target(event.src_path):
            logger.info(f"[watcher] 検知: 変更 {event.src_path}")
            self._schedule_sync()

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_target(event.src_path):
            logger.info(f"[watcher] 検知: 削除 {event.src_path}")
            self._schedule_sync()

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory and (
            self._is_target(event.src_path) or self._is_target(event.dest_path)
        ):
            logger.info(f"[watcher] 検知: 移動 {event.src_path} → {event.dest_path}")
            self._schedule_sync()


class KnowledgeWatcher:
    """ナレッジディレクトリを監視し、変更時に自動同期を実行するクラス。"""

    def __init__(self, on_sync_complete: Callable[[dict], None] | None = None):
        self._observer: Observer | None = None
        self._running = False
        self._last_sync_result: dict | None = None
        self._on_sync_complete = on_sync_complete
        self._sync_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_sync_result(self) -> dict | None:
        return self._last_sync_result

    def _do_sync(self) -> None:
        """同期処理を実行する。"""
        if not self._sync_lock.acquire(blocking=False):
            logger.info("[watcher] 同期が既に実行中のためスキップ")
            return
        try:
            from sync import run_sync
            knowledge_path = Path(config.knowledge_path)
            if not knowledge_path.exists():
                return
            logger.info("[watcher] 自動同期を開始...")
            stats = run_sync(knowledge_path)
            self._last_sync_result = {
                "stats": stats,
                "timestamp": time.time(),
            }
            logger.info(
                f"[watcher] 自動同期完了: 追加 {stats['added']}, 更新 {stats['updated']}, "
                f"削除 {stats['deleted']}, スキップ {stats['skipped']}"
            )
            if self._on_sync_complete:
                self._on_sync_complete(self._last_sync_result)
        except Exception:
            logger.exception("[watcher] 自動同期でエラーが発生")
        finally:
            self._sync_lock.release()

    def start(self) -> None:
        """監視を開始する。"""
        if self._running:
            return

        watch_path = Path(config.knowledge_path)
        watch_path.mkdir(parents=True, exist_ok=True)

        handler = _KnowledgeEventHandler(on_change=self._do_sync)
        self._observer = Observer()
        self._observer.schedule(handler, str(watch_path), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        self._running = True
        logger.info(f"[watcher] 監視開始: {watch_path}")

    def stop(self) -> None:
        """監視を停止する。"""
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            self._running = False
            logger.info("[watcher] 監視停止")
