"""config モジュールのテスト。"""
import os

from src.config import Config


def test_default_values():
    """デフォルト値が正しく設定されていること。"""
    cfg = Config()
    assert cfg.pg_host == os.getenv("PG_HOST", "localhost")
    assert cfg.pg_port == int(os.getenv("PG_PORT", "5432"))
    assert cfg.pg_db == os.getenv("PG_DB", "log_assistant")
    assert cfg.chunk_size == int(os.getenv("CHUNK_SIZE", "800"))
    assert cfg.chunk_overlap == int(os.getenv("CHUNK_OVERLAP", "100"))


def test_pg_dsn():
    """pg_dsnが正しい形式で生成されること。"""
    cfg = Config()
    assert cfg.pg_dsn.startswith("postgresql://")
    assert cfg.pg_db in cfg.pg_dsn


def test_knowledge_path_default():
    """knowledge_pathのデフォルト値。"""
    cfg = Config()
    assert "knowledge" in cfg.knowledge_path


def test_templates_path_default():
    """templates_pathのデフォルト値。"""
    cfg = Config()
    assert "templates" in cfg.templates_path
