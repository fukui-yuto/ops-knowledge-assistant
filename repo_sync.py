"""リポジトリ同期CLI。外部Gitリポジトリのpull + knowledge/への配置。"""
from __future__ import annotations

import argparse
import sys

from src.repo_sync import load_repos_config, sync_all_repos, sync_single_repo


def main():
    parser = argparse.ArgumentParser(
        description="リポジトリ同期 - 外部Gitリポジトリをpullしてknowledge/に配置する"
    )
    parser.add_argument("--name", type=str, help="特定リポジトリのみ同期する")
    parser.add_argument("--list", action="store_true", help="登録済みリポジトリ一覧を表示")
    args = parser.parse_args()

    if args.list:
        repos = load_repos_config()
        if not repos:
            print("登録されたリポジトリはありません。")
            return
        for r in repos:
            paths = r.get("paths", {})
            path_info = ", ".join(f"{k}={v}" for k, v in paths.items())
            print(f"  {r['name']}: {r.get('url', '')} ({path_info})")
        return

    if args.name:
        result = sync_single_repo(args.name)
        if result["status"] == "ok":
            print(f"[repo] {result['name']}: 同期完了 (コピー {result.get('copied', 0)}, 削除 {result.get('removed', 0)})")
        else:
            print(f"[repo] {result['name']}: エラー - {result.get('error', '不明')}", file=sys.stderr)
            sys.exit(1)
        return

    results = sync_all_repos()
    if not results:
        print("登録されたリポジトリはありません。")
        return

    for r in results:
        if r["status"] == "ok":
            print(f"[repo] {r['name']}: 同期完了 (コピー {r.get('copied', 0)}, 削除 {r.get('removed', 0)})")
        else:
            print(f"[repo] {r['name']}: エラー - {r.get('error', '不明')}", file=sys.stderr)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    print(f"[repo] 完了: {ok_count}/{len(results)} repos synced")


if __name__ == "__main__":
    sys.exit(main())
