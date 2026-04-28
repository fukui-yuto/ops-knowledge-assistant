"""ops-knowledge-assistant Web GUI (Streamlit)"""
import logging
import threading
import time

import streamlit as st

from src.config import config
from src.watcher import KnowledgeWatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ops-knowledge-assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ファイル監視の自動起動 ---
if "watcher" not in st.session_state:
    watcher = KnowledgeWatcher()
    watcher.start()
    st.session_state["watcher"] = watcher

# --- リポジトリ定期同期の自動起動 ---
if "repo_sync_thread" not in st.session_state:
    def _repo_sync_loop():
        """バックグラウンドでリポジトリ同期を定期実行する。"""
        while True:
            time.sleep(config.repo_sync_interval)
            try:
                from src.repo_sync import sync_all_repos
                results = sync_all_repos()
                for r in results:
                    if r["status"] == "ok":
                        logger.info(
                            f"[repo-timer] {r['name']}: コピー {r.get('copied', 0)}, "
                            f"削除 {r.get('removed', 0)}"
                        )
                    else:
                        logger.error(f"[repo-timer] {r['name']}: {r.get('error', '')}")
            except Exception:
                logger.exception("[repo-timer] リポジトリ同期でエラーが発生")

    t = threading.Thread(target=_repo_sync_loop, daemon=True)
    t.start()
    st.session_state["repo_sync_thread"] = t

st.title("ops-knowledge-assistant")
st.markdown("テンプレート + 過去手順から新規手順書を自動生成するシステム")
st.markdown("---")
st.markdown("左のサイドバーからページを選択してください。")

# --- サイドバーにファイル監視ステータスを表示 ---
watcher: KnowledgeWatcher = st.session_state["watcher"]
if watcher.is_running:
    st.sidebar.caption("🟢 ナレッジ自動同期: 有効")
else:
    st.sidebar.caption("🔴 ナレッジ自動同期: 停止")

last = watcher.last_sync_result
if last:
    import datetime
    ts = datetime.datetime.fromtimestamp(last["timestamp"]).strftime("%H:%M:%S")
    s = last["stats"]
    st.sidebar.caption(
        f"最終同期: {ts} "
        f"(+{s['added']} △{s['updated']} -{s['deleted']})"
    )

st.sidebar.success("ページを選択してください。")
