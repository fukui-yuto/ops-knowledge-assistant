"""ナレッジ管理ページ"""
import tempfile
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

col1, col2 = st.columns(2)
with col1:
    source_type = st.selectbox("種別", ["procedure", "ticket", "config", "log"])
with col2:
    source_system = st.text_input("システム", placeholder="confluence, jira, proxmox 等")

uploaded_file = st.file_uploader("Markdownファイルを選択", type=["md"])

if st.button("アップロード", disabled=not (uploaded_file and source_system)):
    try:
        pipeline = get_pipeline()

        # 一時ファイルに保存して取り込み
        import re
        content = uploaded_file.read().decode("utf-8")
        filename = Path(uploaded_file.name).stem
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filename

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            tmp_path = f.name

        result = pipeline.ingest_file(
            src_path=tmp_path,
            source_type=source_type,
            source_system=source_system,
            external_id=filename,
            title=title,
        )

        Path(tmp_path).unlink(missing_ok=True)

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
def load_documents(type_filter, system_filter):
    from src import db
    return db.list_documents(
        source_type=type_filter if type_filter != "全て" else None,
        source_system=system_filter if system_filter != "全て" else None,
    )


col_f1, col_f2 = st.columns(2)
with col_f1:
    type_filter = st.selectbox("種別フィルタ", ["全て", "procedure", "ticket", "config", "log"], key="filter_type")
with col_f2:
    system_filter = st.text_input("システムフィルタ", value="全て", key="filter_system")

try:
    docs = load_documents(type_filter, system_filter)

    if docs:
        for doc in docs:
            col_a, col_b, col_c, col_d, col_e = st.columns([2, 3, 2, 1, 1])
            col_a.write(doc["source_type"])
            col_b.write(doc["title"])
            col_c.write(doc.get("source_system", ""))
            col_d.write(str(doc.get("chunk_count", 0)))

            if col_e.button("🗑", key=f"del_{doc['id']}"):
                try:
                    from src import db as db_module
                    from src.vector_store import VectorStore

                    vector_ids = db_module.delete_document(doc["id"])
                    if vector_ids:
                        vstore = VectorStore()
                        vstore.delete(doc["source_type"], vector_ids)
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
