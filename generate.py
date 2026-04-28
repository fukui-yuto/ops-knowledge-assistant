"""手順書生成CLI。タイトルだけで新規手順書を生成する。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.generator import ProcedureGenerator


def main():
    parser = argparse.ArgumentParser(
        description="新規手順書を生成する",
        usage="python generate.py \"タイトル\" [オプション]",
    )
    parser.add_argument("title", nargs="?", help="生成する手順書のタイトル")
    parser.add_argument("-d", "--description", default="", help="手順の詳細説明（省略可）")
    parser.add_argument("-t", "--template", default="", help="テンプレート名（省略時は自動選定）")
    parser.add_argument("-c", "--context", default="", help="追加コンテキスト")
    parser.add_argument("-o", "--output", default="", help="出力ファイルパス（省略時はstdout）")
    parser.add_argument("--max-references", type=int, default=3, help="参照する過去手順の最大数")
    parser.add_argument("--list-templates", action="store_true", help="テンプレート一覧を表示")
    args = parser.parse_args()

    generator = ProcedureGenerator()

    if args.list_templates:
        templates = generator.list_templates()
        if templates:
            print("利用可能なテンプレート:")
            for t in templates:
                print(f"  - {t}")
        else:
            print("テンプレートが見つかりません（data/templates/ にMarkdownファイルを配置してください）")
        return

    if not args.title:
        parser.error("タイトルを指定してください（例: python generate.py \"PostgreSQL バックアップ手順\"）")

    # 進捗表示（stderrへ）
    template_name = args.template or generator.auto_select_template(args.title)
    print(f"生成中: {args.title}", file=sys.stderr)
    print(f"テンプレート: {template_name}", file=sys.stderr)
    print(f"関連手順を検索中...", file=sys.stderr)

    result = generator.generate(
        title=args.title,
        description=args.description,
        template_name=args.template,
        max_references=args.max_references,
        extra_context=args.context,
    )

    # メタ情報表示
    info = generator.last_generation_info
    if info["todo_count"] > 0:
        print(f"[警告] TODO項目が {info['todo_count']} 件あります。確認してください。", file=sys.stderr)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(f"保存先: {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    sys.exit(main())
