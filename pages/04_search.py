"""ナレッジ検索ページ"""
import streamlit as st

st.set_page_config(page_title="検索", page_icon="🔍", layout="wide")
st.title("🔍 ナレッジ検索")


@st.cache_resource
def get_retriever():
    from src.retriever import Retriever
    return Retriever()


query = st.text_input("検索クエリ", placeholder="例: Proxmox バックアップ")

col1, col2 = st.columns(2)
with col1:
    source_type_filter = st.selectbox("種別フィルタ", ["全て", "procedure", "ticket", "config", "log"])
with col2:
    n_results = st.slider("検索結果数", 1, 20, 5)

if st.button("検索", disabled=not query):
    try:
        retriever = get_retriever()

        where = None
        if source_type_filter != "全て":
            where = {"source_type": source_type_filter}

        # procedure コレクションで検索（他のtypeも順次対応）
        search_type = source_type_filter if source_type_filter != "全て" else "procedure"
        results = retriever.search_procedures(query, n_results=n_results, where=where)

        if results:
            st.markdown(f"### 検索結果 ({len(results)} 件)")
            for i, hit in enumerate(results, 1):
                distance = hit.get("distance", None)
                similarity = f"{1 - distance:.2f}" if distance is not None else "N/A"

                with st.expander(f"{i}. {hit.get('title', '(タイトル不明)')} (類似度: {similarity})"):
                    st.caption(f"source: {hit.get('source_system', '')} | external_id: {hit.get('external_id', '')}")
                    st.markdown(hit.get("chunk_content", ""))

                    if st.button(f"全文を見る", key=f"full_{i}"):
                        doc_id = hit.get("document_id", "")
                        if doc_id:
                            full_text = retriever.get_full_document_text(doc_id)
                            st.markdown(full_text)
        else:
            st.info("該当する結果がありませんでした。")

    except Exception as e:
        st.error(f"検索エラー: {e}")
        st.info("PostgreSQL と ChromaDB が起動しているか確認してください。")
