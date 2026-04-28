"""CLI: generate a new procedure document.

Usage:
  python -m scripts.generate_cli \
      --title "Proxmox バックアップ手順" \
      --description "Proxmox VEの全VMを日次バックアップする手順を作成" \
      --template default \
      --output output/proxmox_backup.md

  # テンプレート一覧
  python -m scripts.generate_cli --list-templates

  # 追加コンテキストを渡す場合
  python -m scripts.generate_cli \
      --title "K8s Pod再起動手順" \
      --description "CrashLoopBackOffになったPodを安全に再起動する" \
      --extra-context "対象クラスタはproduction、namespace=app"
"""
import argparse
import sys
from pathlib import Path

from src.generator import ProcedureGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate a new procedure document")
    parser.add_argument("--title", help="Procedure title")
    parser.add_argument("--description", help="What the procedure should cover")
    parser.add_argument("--template", default="default", help="Template name (default: default)")
    parser.add_argument("--max-references", type=int, default=3, help="Max past procedures to reference")
    parser.add_argument("--extra-context", default="", help="Additional context for generation")
    parser.add_argument("--output", help="Output file path (if omitted, prints to stdout)")
    parser.add_argument("--list-templates", action="store_true", help="List available templates")
    args = parser.parse_args()

    generator = ProcedureGenerator()

    if args.list_templates:
        templates = generator.list_templates()
        if templates:
            print("Available templates:")
            for t in templates:
                print(f"  - {t}")
        else:
            print("No templates found in data/templates/")
        return

    if not args.title or not args.description:
        parser.error("--title and --description are required")

    print(f"Generating: {args.title}", file=sys.stderr)
    print(f"Template: {args.template}", file=sys.stderr)
    print(f"Searching related procedures...", file=sys.stderr)

    result = generator.generate(
        title=args.title,
        description=args.description,
        template_name=args.template,
        max_references=args.max_references,
        extra_context=args.extra_context,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(f"Saved to: {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    sys.exit(main())
