"""設定・ステータスページ"""
import streamlit as st

from src.config import config

st.set_page_config(page_title="設定", page_icon="⚙", layout="wide")
st.title("⚙ 設定・ステータス")

# --- システム状態 ---
st.markdown("### システム状態")

col1, col2, col3 = st.columns(3)

# PostgreSQL
with col1:
    try:
        from src import db
        stats = db.get_stats()
        st.success(f"PostgreSQL: 接続中 ({config.pg_db})")
    except Exception as e:
        st.error(f"PostgreSQL: 接続エラー")
        stats = None

# ChromaDB
with col2:
    try:
        from src.vector_store import VectorStore
        vstore = VectorStore()
        st.success("ChromaDB: 正常")
    except Exception as e:
        st.error(f"ChromaDB: エラー")

# Gemini API
with col3:
    if config.google_api_key:
        st.success("Gemini API: キー設定済み")
    else:
        st.error("Gemini API: キー未設定")

# --- 統計 ---
if stats:
    st.markdown("### 統計")
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("ドキュメント数", stats["documents"])
    col_s2.metric("チャンク数", stats["chunks"])

    from pathlib import Path
    templates_dir = Path(config.templates_path)
    template_count = len(list(templates_dir.glob("*.md"))) if templates_dir.exists() else 0
    col_s3.metric("テンプレート数", template_count)

# --- 整合性チェック ---
st.markdown("### 整合性チェック")
if st.button("チェック実行"):
    try:
        from src.vector_store import VectorStore
        vstore = VectorStore()
        results = []
        for stype in ["procedure", "ticket", "config", "log"]:
            try:
                col = vstore._collection(stype)
                count = col.count()
                results.append(f"  ChromaDB [{stype}]: {count} vectors")
            except Exception:
                results.append(f"  ChromaDB [{stype}]: コレクションなし")

        if stats:
            results.insert(0, f"  PostgreSQL: {stats['documents']} documents, {stats['chunks']} chunks")

        st.code("\n".join(results))
        st.success("チェック完了")
    except Exception as e:
        st.error(f"チェックエラー: {e}")

# --- データベース操作 ---
st.markdown("### データベース操作")

col_d1, col_d2 = st.columns(2)
with col_d1:
    if st.button("スキーマ初期化"):
        try:
            from src import db
            db.init_schema()
            st.success("スキーマを適用しました")
        except Exception as e:
            st.error(f"スキーマ適用エラー: {e}")

# --- 設定値 ---
st.markdown("### 現在の設定")
st.json({
    "PG_HOST": config.pg_host,
    "PG_PORT": config.pg_port,
    "PG_DB": config.pg_db,
    "CHROMA_PATH": config.chroma_path,
    "KNOWLEDGE_PATH": config.knowledge_path,
    "TEMPLATES_PATH": config.templates_path,
    "EMBEDDING_MODEL": config.embedding_model,
    "GENERATION_MODEL": config.generation_model,
    "CHUNK_SIZE": config.chunk_size,
    "CHUNK_OVERLAP": config.chunk_overlap,
    "GOOGLE_API_KEY": "***" if config.google_api_key else "(未設定)",
})
