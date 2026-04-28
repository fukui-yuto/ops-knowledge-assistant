"""ヘルスチェックスクリプト。Docker HEALTHCHECK および監視用。"""
from __future__ import annotations

import sys

from src.config import config


def check_postgres() -> bool:
    """PostgreSQL への接続を確認する。"""
    import psycopg2

    try:
        conn = psycopg2.connect(config.pg_dsn)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[NG] PostgreSQL: {e}", file=sys.stderr)
        return False


def check_chroma() -> bool:
    """ChromaDB のコレクションアクセスを確認する。"""
    try:
        from src.vector_store import VectorStore

        vstore = VectorStore()
        vstore._collection("wiki")
        return True
    except Exception as e:
        print(f"[NG] ChromaDB: {e}", file=sys.stderr)
        return False


def check_llm_api_key() -> bool:
    """現在のLLMプロバイダのAPIキーが設定されているか確認する。"""
    provider = config.llm_provider
    if provider == "openai":
        if not config.openai_api_key:
            print("[NG] OPENAI_API_KEY: 未設定", file=sys.stderr)
            return False
    else:
        if not config.google_api_key:
            print("[NG] GOOGLE_API_KEY: 未設定", file=sys.stderr)
            return False
    return True


def main() -> int:
    provider = config.llm_provider
    api_key_label = "OPENAI_API_KEY" if provider == "openai" else "GOOGLE_API_KEY"

    results = {
        "PostgreSQL": check_postgres(),
        "ChromaDB": check_chroma(),
        f"{api_key_label} (provider={provider})": check_llm_api_key(),
    }

    all_ok = all(results.values())

    for name, ok in results.items():
        status = "OK" if ok else "NG"
        print(f"[{status}] {name}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
