"""リポジトリ管理ページ"""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="リポジトリ管理", page_icon="🔗", layout="wide")
st.title("🔗 リポジトリ管理")

from src.config import config
from src.repo_sync import (
    clone_repo,
    delete_repo,
    list_directory_tree,
    load_repos_config,
    save_repos_config,
    sync_all_repos,
    sync_single_repo,
)

# --- 登録セクション ---
st.markdown("### リポジトリの登録")

with st.form("add_repo_form"):
    col1, col2 = st.columns([3, 1])
    repo_url = col1.text_input("リポジトリURL", placeholder="https://github.com/org/repo.git")
    repo_branch = col2.text_input("ブランチ", value="main")

    col3, col4 = st.columns([2, 2])
    repo_name = col3.text_input("リポジトリ名（一意の識別名）", placeholder="team-a")
    token_env = col4.text_input("トークン環境変数名（任意）", placeholder="REPO_TOKEN_TEAM_A")

    clone_btn = st.form_submit_button("クローンして構造を確認")

if clone_btn and repo_url and repo_name:
    try:
        with st.spinner("クローン中..."):
            clone_repo(repo_url, repo_name, repo_branch, token_env or None)
        st.success(f"クローン完了: {repo_name}")

        # ディレクトリツリーを表示
        tree = list_directory_tree(repo_name)
        dirs = [t for t in tree if t["is_dir"] and t["has_md"]]

        if dirs:
            st.markdown("**Markdownファイルを含むディレクトリ:**")
            dir_paths = [d["path"] for d in dirs]

            wiki_paths = st.multiselect(
                "Wiki パス（運用手順書の配置先、複数選択可）",
                dir_paths,
                key="wiki_path_select",
            )
            issue_paths = st.multiselect(
                "Issue パス（障害対応記録の配置先、複数選択可）",
                dir_paths,
                key="issue_path_select",
            )

            if st.button("設定を保存"):
                paths = {}
                if wiki_paths:
                    paths["wiki"] = wiki_paths if len(wiki_paths) > 1 else wiki_paths[0]
                if issue_paths:
                    paths["issue"] = issue_paths if len(issue_paths) > 1 else issue_paths[0]

                if not paths:
                    st.warning("wiki または issue のパスを1つ以上選択してください。")
                else:
                    repos = load_repos_config()
                    # 既存エントリを更新 or 追加
                    existing = next((r for r in repos if r["name"] == repo_name), None)
                    entry = {
                        "name": repo_name,
                        "url": repo_url,
                        "branch": repo_branch,
                        "paths": paths,
                    }
                    if token_env:
                        entry["token_env"] = token_env
                    if existing:
                        repos = [entry if r["name"] == repo_name else r for r in repos]
                    else:
                        repos.append(entry)
                    save_repos_config(repos)
                    st.success("設定を保存しました。「同期実行」でファイルを取り込めます。")
                    st.rerun()
        else:
            st.warning("Markdownファイルを含むディレクトリが見つかりません。")

    except Exception as e:
        st.error(f"クローンエラー: {e}")

# --- 登録済みリポジトリ一覧 ---
st.markdown("---")
st.markdown("### 登録済みリポジトリ")

repos = load_repos_config()

if repos:
    for repo in repos:
        name = repo["name"]
        paths = repo.get("paths", {})
        path_info = ", ".join(
            f"{k}: {v if isinstance(v, str) else ', '.join(v)}"
            for k, v in paths.items()
        )

        with st.expander(f"📁 {name} — {repo.get('url', '')}"):
            st.markdown(f"**ブランチ:** {repo.get('branch', 'main')}")
            st.markdown(f"**パスマッピング:** {path_info}")
            if repo.get("token_env"):
                st.markdown(f"**トークン:** `{repo['token_env']}`")

            col_sync, col_del = st.columns([1, 1])

            if col_sync.button("同期実行", key=f"sync_{name}"):
                with st.spinner(f"{name} を同期中..."):
                    result = sync_single_repo(name)
                if result["status"] == "ok":
                    st.success(
                        f"同期完了: コピー {result.get('copied', 0)}, "
                        f"削除 {result.get('removed', 0)}"
                    )
                else:
                    st.error(f"同期エラー: {result.get('error', '不明')}")

            if col_del.button("削除", key=f"del_{name}"):
                try:
                    delete_repo(name)
                    st.success(f"{name} を削除しました。")
                    st.rerun()
                except Exception as e:
                    st.error(f"削除エラー: {e}")
else:
    st.info("登録されたリポジトリはありません。上のフォームからリポジトリを追加してください。")

# --- 一括同期 ---
st.markdown("---")
if st.button("全リポジトリを一括同期"):
    if not repos:
        st.warning("登録されたリポジトリがありません。")
    else:
        with st.spinner("全リポジトリを同期中..."):
            results = sync_all_repos()
        for r in results:
            if r["status"] == "ok":
                st.success(
                    f"{r['name']}: コピー {r.get('copied', 0)}, "
                    f"削除 {r.get('removed', 0)}"
                )
            else:
                st.error(f"{r['name']}: {r.get('error', '不明')}")
