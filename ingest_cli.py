"""CLI: ingest a single file.

Usage:
  python -m scripts.ingest_cli \
      --path data/sample/proxmox_node_add.md \
      --source-type procedure \
      --source-system confluence \
      --external-id PROC-001 \
      --title "Proxmox ノード追加手順"
"""
import argparse
import json
import sys

from src import db
from src.ingestion import IngestionPipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument(
        "--source-type",
        required=True,
        choices=["procedure", "ticket", "config", "log"],
    )
    parser.add_argument("--source-system", required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--metadata", default="{}", help="JSON string")
    parser.add_argument("--ticket-fields", default=None, help="JSON string")
    parser.add_argument("--init-schema", action="store_true")
    args = parser.parse_args()

    if args.init_schema:
        db.init_schema()
        print("[ok] schema applied")

    pipeline = IngestionPipeline()
    result = pipeline.ingest_file(
        src_path=args.path,
        source_type=args.source_type,
        source_system=args.source_system,
        external_id=args.external_id,
        title=args.title,
        metadata=json.loads(args.metadata),
        ticket_fields=json.loads(args.ticket_fields) if args.ticket_fields else None,
    )
    print(json.dumps(result, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
