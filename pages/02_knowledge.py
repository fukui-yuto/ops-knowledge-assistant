"""ナレッジ管理ページ"""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="ナレッジ管理", page_icon="📚", layout="wide")
st.title("📚 ナレッジ管理")


@st.cache_resource
def get_pipeline():
    from src.ingestion import IngestionPipeline
    return IngestionPipeline()


# --- アップロードセクション ---
st.markdown("### ファイルアップロード")

source_type = st.selectbox("種別", ["wiki", "issue"])

uploaded_file = st.file_uploader("Markdownファイルを選択", type=["md"])

if st.button("アップロード", disabled=not uploaded_file):
    try:
        pipeline = get_pipeline()

        import re
        from src.config import config

        content = uploaded_file.read().decode("utf-8")
        filename = Path(uploaded_file.name).stem
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filename

        # data/knowledge/{type}/local/ にファイルを配置（sync.py との整合性を保つ）
        knowledge_dir = Path(config.knowledge_path) / source_type / "local"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        knowledge_file = knowledge_dir / f"{filename}.md"
        knowledge_file.write_text(content, encoding="utf-8")

        result = pipeline.ingest_file(
            src_path=str(knowledge_file),
            source_type=source_type,
            source_system="local",
            external_id=filename,
            title=title,
        )

        if result["action"] == "created":
            st.success(f"追加しました: 「{title}」 ({result['chunks']} chunks)")
        elif result["action"] == "updated":
            st.info(f"更新しました: 「{title}」 ({result['chunks']} chunks)")
        else:
            st.warning(f"スキップ: 「{title}」 (変更なし)")

        st.cache_data.clear()

    except Exception as e:
        st.error(f"アップロードエラー: {e}")

# --- 一覧セクション ---
st.markdown("---")
st.markdown("### 登録済みナレッジ一覧")


@st.cache_data(ttl=10)
def load_documents(type_filter):
    from src import db
    return db.list_documents(
        source_type=type_filter if type_filter != "全て" else None,
    )


type_filter = st.selectbox("種別フィルタ", ["全て", "wiki", "issue"], key="filter_type")

try:
    docs = load_documents(type_filter)

    if docs:
        for doc in docs:
            col_a, col_b, col_c, col_d = st.columns([2, 4, 1, 1])
            col_a.write(doc["source_type"])
            col_b.write(doc["title"])
            col_c.write(str(doc.get("chunk_count", 0)))

            if col_d.button("🗑", key=f"del_{doc['id']}"):
                try:
                    from src import db as db_module
                    from src.config import config as app_config
                    from src.storage import LocalStorage
                    from src.vector_store import VectorStore

                    # DB + ChromaDB から削除
                    vector_ids = db_module.delete_document(doc["id"])
                    if vector_ids:
                        vstore = VectorStore()
                        vstore.delete(doc["source_type"], vector_ids)

                    # data/knowledge/ からも削除（パストラバーサル防止）
                    ext_id = doc.get("external_id", "")
                    stype = doc["source_type"]
                    ssys = doc.get("source_system", "local")
                    if ext_id:
                        base = Path(app_config.knowledge_path).resolve()
                        kf = (base / stype / ssys / f"{ext_id}.md").resolve()
                        if str(kf).startswith(str(base)):
                            kf.unlink(missing_ok=True)

                    # data/raw/ からも削除
                    if ext_id and ".." not in ext_id:
                        storage = LocalStorage(app_config.raw_storage_path)
                        storage.delete(f"{stype}/{ext_id}.md")

                    st.success(f"削除しました: {doc['title']}")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"削除エラー: {e}")

        st.caption(f"合計: {len(docs)} 件")
    else:
        st.info("ナレッジが登録されていません。ファイルをアップロードしてください。")
except Exception as e:
    st.warning(f"一覧の取得に失敗しました: {e}")
    st.info("PostgreSQL が起動しているか確認してください。")
