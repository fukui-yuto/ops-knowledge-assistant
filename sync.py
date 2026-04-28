"""ナレッジ同期CLI。data/knowledge/ にファイルを置いて実行するだけで取り込み完了。"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from src import db
from src.config import config
from src.ingestion import IngestionPipeline
from src.storage import LocalStorage
from src.vector_store import VectorStore

VALID_SOURCE_TYPES = {"procedure", "ticket", "config", "log"}


def extract_title_from_md(text: str, filename: str) -> str:
    """Markdownファイルの最初の # 見出しからタイトルを抽出する。"""
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return filename.replace("_", " ").replace("-", " ")


def scan_knowledge_dir(knowledge_path: Path) -> list[dict[str, Any]]:
    """ナレッジディレクトリを走査し、取り込み対象のファイル情報を収集する。"""
    files: list[dict[str, Any]] = []

    if not knowledge_path.exists():
        return files

    for source_type_dir in sorted(knowledge_path.iterdir()):
        if not source_type_dir.is_dir():
            continue
        source_type = source_type_dir.name
        if source_type not in VALID_SOURCE_TYPES:
            continue

        for source_system_dir in sorted(source_type_dir.iterdir()):
            if not source_system_dir.is_dir():
                continue
            source_system = source_system_dir.name

            for md_file in sorted(source_system_dir.glob("*.md")):
                text = md_file.read_text(encoding="utf-8")
                external_id = md_file.stem
                title = extract_title_from_md(text, external_id)
                content_hash = LocalStorage.hash_text(text)

                files.append({
                    "path": md_file,
                    "source_type": source_type,
                    "source_system": source_system,
                    "external_id": external_id,
                    "title": title,
                    "content_hash": content_hash,
                })

    return files


def run_sync(
    knowledge_path: Path,
    dry_run: bool = False,
) -> dict[str, int]:
    """ナレッジディレクトリとDBを同期する。"""
    pipeline = IngestionPipeline()
    vstore = VectorStore()
    stats = {"added": 0, "updated": 0, "skipped": 0, "deleted": 0, "errors": 0}

    # 1. ナレッジディレクトリを走査
    files = scan_knowledge_dir(knowledge_path)
    file_keys = set()

    # 2. 各ファイルを処理
    for f in files:
        key = (f["source_system"], f["external_id"])
        file_keys.add(key)

        if dry_run:
            print(f"[dry-run] {f['source_type']}/{f['source_system']}/{f['external_id']}.md → \"{f['title']}\"")
            continue

        try:
            result = pipeline.ingest_file(
                src_path=f["path"],
                source_type=f["source_type"],
                source_system=f["source_system"],
                external_id=f["external_id"],
                title=f["title"],
            )
            action = result["action"]
            if action == "created":
                print(f"[add]    {f['source_type']}/{f['source_system']}/{f['external_id']}.md → \"{f['title']}\" ({result['chunks']} chunks)")
                stats["added"] += 1
            elif action == "updated":
                print(f"[update] {f['source_type']}/{f['source_system']}/{f['external_id']}.md → \"{f['title']}\" ({result['chunks']} chunks)")
                stats["updated"] += 1
            else:
                print(f"[skip]   {f['source_type']}/{f['source_system']}/{f['external_id']}.md (変更なし)")
                stats["skipped"] += 1
        except Exception as e:
            print(f"[error]  {f['source_type']}/{f['source_system']}/{f['external_id']}.md → {e}", file=sys.stderr)
            stats["errors"] += 1

    # 3. DB にあるがディレクトリにないファイルを削除
    existing_docs = db.get_all_external_ids()
    for (sys_name, ext_id), doc_id in existing_docs.items():
        if (sys_name, ext_id) not in file_keys:
            if dry_run:
                print(f"[dry-run] 削除対象: {sys_name}/{ext_id}")
                continue
            try:
                # source_type を取得してChromaDB からも削除
                docs = db.fetch_documents_by_ids([doc_id])
                source_type = docs[0]["source_type"] if docs else "procedure"
                vector_ids = db.delete_document(doc_id)
                if vector_ids:
                    vstore.delete(source_type, vector_ids)
                # raw storage からも削除
                pipeline.storage.delete(f"{source_type}/{sys_name}/{ext_id}.md")
                print(f"[delete] {sys_name}/{ext_id} → DB + ChromaDB から削除")
                stats["deleted"] += 1
            except Exception as e:
                print(f"[error]  削除失敗 {sys_name}/{ext_id}: {e}", file=sys.stderr)
                stats["errors"] += 1

    return stats


def run_check() -> None:
    """整合性チェックを実行する。"""
    print("[check] 整合性チェックを実行中...")
    try:
        stats = db.get_stats()
        print(f"  PostgreSQL: {stats['documents']} documents, {stats['chunks']} chunks")
    except Exception as e:
        print(f"  PostgreSQL: 接続エラー - {e}", file=sys.stderr)
        return

    try:
        vstore = VectorStore()
        for source_type in VALID_SOURCE_TYPES:
            try:
                col = vstore._collection(source_type)
                count = col.count()
                print(f"  ChromaDB [{source_type}]: {count} vectors")
            except Exception:
                print(f"  ChromaDB [{source_type}]: コレクションなし")
    except Exception as e:
        print(f"  ChromaDB: エラー - {e}", file=sys.stderr)

    print("[check] 完了")


def main():
    parser = argparse.ArgumentParser(
        description="ナレッジ同期 - data/knowledge/ のファイルをDBに同期する"
    )
    parser.add_argument("--init-schema", action="store_true", help="初回: DBスキーマを適用する")
    parser.add_argument("--check", action="store_true", help="整合性チェックのみ実行する")
    parser.add_argument("--dry-run", action="store_true", help="実行予定の操作を表示するが変更しない")
    args = parser.parse_args()

    if args.init_schema:
        db.init_schema()
        print("[ok] スキーマを適用しました")

    if args.check:
        run_check()
        return

    knowledge_path = Path(config.knowledge_path)
    if not knowledge_path.exists():
        knowledge_path.mkdir(parents=True, exist_ok=True)
        print(f"[info] ナレッジディレクトリを作成しました: {knowledge_path}")
        print("[info] data/knowledge/procedure/<system>/ 等にMarkdownファイルを配置してください")
        return

    print(f"[sync] {knowledge_path} を走査中...")
    stats = run_sync(knowledge_path, dry_run=args.dry_run)
    print(f"[sync] 完了: 追加 {stats['added']}, 更新 {stats['updated']}, "
          f"スキップ {stats['skipped']}, 削除 {stats['deleted']}"
          + (f", エラー {stats['errors']}" if stats['errors'] else ""))


if __name__ == "__main__":
    sys.exit(main())
