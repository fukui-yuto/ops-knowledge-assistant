"""外部Gitリポジトリの同期。clone/pull → knowledge/ へファイル配置。"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml
from git import Repo
from git.exc import GitCommandError

from .config import config

logger = logging.getLogger(__name__)

VALID_SOURCE_TYPES = {"wiki", "issue"}


def load_repos_config() -> list[dict[str, Any]]:
    """repos.yaml からリポジトリ設定を読み込む。"""
    config_path = Path(config.repos_config_path)
    if not config_path.exists():
        return []
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "repos" not in data:
        return []
    return data["repos"]


def save_repos_config(repos: list[dict[str, Any]]) -> None:
    """リポジトリ設定を repos.yaml に保存する。"""
    config_path = Path(config.repos_config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump({"repos": repos}, f, allow_unicode=True, default_flow_style=False)


def _get_repo_url_with_token(url: str, token_env: str | None) -> str:
    """トークンを含むURLを生成する。"""
    if not token_env:
        return url
    token = os.getenv(token_env, "")
    if not token:
        logger.warning(f"環境変数 {token_env} が設定されていません")
        return url
    # https://github.com/... → https://{token}@github.com/...
    if url.startswith("https://"):
        return url.replace("https://", f"https://{token}@", 1)
    return url


def clone_repo(url: str, name: str, branch: str = "main", token_env: str | None = None) -> Path:
    """リポジトリをクローンする。既にクローン済みの場合は既存パスを返す。"""
    repos_dir = Path(config.repos_data_path)
    repos_dir.mkdir(parents=True, exist_ok=True)
    repo_path = repos_dir / name

    auth_url = _get_repo_url_with_token(url, token_env)

    if repo_path.exists():
        logger.info(f"[repo] {name}: 既にクローン済み")
        return repo_path

    logger.info(f"[repo] {name}: git clone...")
    Repo.clone_from(auth_url, str(repo_path), branch=branch)
    logger.info(f"[repo] {name}: クローン完了")
    return repo_path


def pull_repo(name: str, url: str | None = None, token_env: str | None = None) -> bool:
    """リポジトリを pull する。変更があれば True を返す。"""
    repo_path = Path(config.repos_data_path) / name
    if not repo_path.exists():
        logger.warning(f"[repo] {name}: クローンされていません")
        return False

    repo = Repo(str(repo_path))
    try:
        # トークンが設定されている場合はリモートURLを更新
        if url and token_env:
            auth_url = _get_repo_url_with_token(url, token_env)
            repo.remotes.origin.set_url(auth_url)

        old_head = repo.head.commit.hexsha
        repo.remotes.origin.pull()
        new_head = repo.head.commit.hexsha
        changed = old_head != new_head
        if changed:
            logger.info(f"[repo] {name}: 更新あり ({old_head[:7]} → {new_head[:7]})")
        else:
            logger.info(f"[repo] {name}: 変更なし")
        return changed
    except GitCommandError as e:
        logger.error(f"[repo] {name}: pull失敗 - {e}")
        return False


def list_directory_tree(repo_name: str) -> list[dict[str, Any]]:
    """リポジトリのディレクトリツリーを返す（GUI用）。"""
    repo_path = Path(config.repos_data_path) / repo_name
    if not repo_path.exists():
        return []

    tree: list[dict[str, Any]] = []
    for item in sorted(repo_path.rglob("*")):
        if ".git" in item.parts:
            continue
        rel = item.relative_to(repo_path)
        tree.append({
            "path": str(rel).replace("\\", "/"),
            "is_dir": item.is_dir(),
            "has_md": any(item.glob("*.md")) if item.is_dir() else False,
        })
    return tree


def _normalize_paths(raw: str | list[str] | None) -> list[str]:
    """パス設定を文字列・リストどちらでもリスト形式に正規化する。"""
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    return [p for p in raw if p and p.strip()]


def sync_repo_files(repo_config: dict[str, Any]) -> dict[str, int]:
    """リポジトリのファイルを knowledge/ にコピーする。

    repo_config:
      name: str
      paths:
        wiki: "docs/procedures" | ["docs/procedures", "docs/runbooks"]
        issue: "docs/incidents" | ["docs/incidents", "docs/postmortems"]
    """
    name = repo_config["name"]
    paths = repo_config.get("paths", {})
    repo_path = Path(config.repos_data_path) / name
    knowledge_path = Path(config.knowledge_path)
    stats = {"copied": 0, "removed": 0}

    if not repo_path.exists():
        logger.warning(f"[repo] {name}: クローンされていません")
        return stats

    for source_type in VALID_SOURCE_TYPES:
        src_rels = _normalize_paths(paths.get(source_type))
        if not src_rels:
            continue

        dst_dir = knowledge_path / source_type / name
        dst_dir.mkdir(parents=True, exist_ok=True)

        # 全パスからコピー元ファイルを収集（後のパスが優先）
        src_file_map: dict[str, Path] = {}
        for src_rel in src_rels:
            src_dir = repo_path / src_rel
            if not src_dir.exists():
                logger.warning(f"[repo] {name}: パス {src_rel} が存在しません")
                continue
            for f in src_dir.glob("*.md"):
                if f.name != "README.md":
                    src_file_map[f.name] = f

        # コピー先の既存ファイル一覧（削除検知用）
        dst_files = {f.name for f in dst_dir.glob("*.md")}

        # 新規・更新ファイルをコピー
        for md_name, src_file in src_file_map.items():
            dst_file = dst_dir / md_name
            if dst_file.exists():
                src_content = src_file.read_bytes()
                dst_content = dst_file.read_bytes()
                if src_content == dst_content:
                    continue
            shutil.copy2(str(src_file), str(dst_file))
            logger.info(f"[repo] {name}: {source_type}/{md_name} をコピー")
            stats["copied"] += 1

        # リポジトリから削除されたファイルを knowledge/ からも削除
        removed = dst_files - set(src_file_map.keys())
        for md_name in removed:
            dst_file = dst_dir / md_name
            dst_file.unlink(missing_ok=True)
            logger.info(f"[repo] {name}: {source_type}/{md_name} を削除")
            stats["removed"] += 1

    return stats


def sync_all_repos() -> list[dict[str, Any]]:
    """全リポジトリを同期する。"""
    repos = load_repos_config()
    results = []

    for repo_cfg in repos:
        name = repo_cfg["name"]
        url = repo_cfg.get("url", "")
        branch = repo_cfg.get("branch", "main")
        token_env = repo_cfg.get("token_env")

        try:
            # clone or pull
            repo_path = Path(config.repos_data_path) / name
            if not repo_path.exists():
                clone_repo(url, name, branch, token_env)
            else:
                pull_repo(name, url, token_env)

            # ファイルをknowledge/へコピー
            stats = sync_repo_files(repo_cfg)
            results.append({"name": name, "status": "ok", **stats})
        except Exception as e:
            logger.error(f"[repo] {name}: 同期失敗 - {e}")
            results.append({"name": name, "status": "error", "error": str(e)})

    return results


def sync_single_repo(name: str) -> dict[str, Any]:
    """特定リポジトリのみ同期する。"""
    repos = load_repos_config()
    repo_cfg = next((r for r in repos if r["name"] == name), None)
    if not repo_cfg:
        return {"name": name, "status": "error", "error": "リポジトリが見つかりません"}

    try:
        url = repo_cfg.get("url", "")
        branch = repo_cfg.get("branch", "main")
        token_env = repo_cfg.get("token_env")

        repo_path = Path(config.repos_data_path) / name
        if not repo_path.exists():
            clone_repo(url, name, branch, token_env)
        else:
            pull_repo(name, url, token_env)

        stats = sync_repo_files(repo_cfg)
        return {"name": name, "status": "ok", **stats}
    except Exception as e:
        logger.error(f"[repo] {name}: 同期失敗 - {e}")
        return {"name": name, "status": "error", "error": str(e)}


def delete_repo(name: str) -> None:
    """リポジトリのクローンと knowledge/ 内のファイルを削除する。"""
    # クローン先を削除
    repo_path = Path(config.repos_data_path) / name
    if repo_path.exists():
        shutil.rmtree(str(repo_path))
        logger.info(f"[repo] {name}: クローンを削除")

    # knowledge/ 内の該当リポジトリのファイルを削除
    knowledge_path = Path(config.knowledge_path)
    for source_type in VALID_SOURCE_TYPES:
        repo_knowledge = knowledge_path / source_type / name
        if repo_knowledge.exists():
            shutil.rmtree(str(repo_knowledge))
            logger.info(f"[repo] {name}: knowledge/{source_type}/{name}/ を削除")

    # repos.yaml から削除
    repos = load_repos_config()
    repos = [r for r in repos if r["name"] != name]
    save_repos_config(repos)
    logger.info(f"[repo] {name}: 設定を削除")
