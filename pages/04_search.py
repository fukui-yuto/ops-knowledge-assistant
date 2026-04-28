"""ナレッジ検索ページ"""
import streamlit as st

st.set_page_config(page_title="検索", page_icon="🔍", layout="wide")
st.title("🔍 ナレッジ検索")


@st.cache_resource
def get_retriever():
    from src.retriever import Retriever
    return Retriever()


query = st.text_input("検索クエリ", placeholder="例: PostgreSQL バックアップ")

col1, col2 = st.columns(2)
with col1:
    source_type_filter = st.selectbox("種別フィルタ", ["全て", "procedure", "ticket", "config", "log"])
with col2:
    n_results = st.slider("検索結果数", 1, 20, 5)

if st.button("検索", disabled=not query):
    try:
        retriever = get_retriever()

        if source_type_filter != "全て":
            results = retriever.search(query, source_type=source_type_filter, n_results=n_results)
        else:
            results = []
            search_errors = []
            for stype in ["procedure", "ticket", "config", "log"]:
                try:
                    hits = retriever.search(query, source_type=stype, n_results=n_results)
                    results.extend(hits)
                except Exception as search_err:
                    search_errors.append(f"{stype}: {search_err}")
            if search_errors:
                st.warning(f"一部コレクションの検索に失敗: {', '.join(search_errors)}")
            results.sort(key=lambda x: x.get("distance", float("inf")))
            results = results[:n_results]

        st.session_state["search_results"] = results
        st.session_state["search_query"] = query

    except Exception as e:
        st.error(f"検索エラー: {e}")
        st.info("PostgreSQL と ChromaDB が起動しているか確認してください。")

# session_state に結果があれば表示
if "search_results" in st.session_state:
    results = st.session_state["search_results"]

    if results:
        st.markdown(f"### 検索結果 ({len(results)} 件)")
        for i, hit in enumerate(results, 1):
            distance = hit.get("distance", None)
            similarity = f"{1 - distance:.2f}" if distance is not None else "N/A"

            with st.expander(f"{i}. {hit.get('title', '(タイトル不明)')} (類似度: {similarity})"):
                st.caption(f"source: {hit.get('source_system', '')} | external_id: {hit.get('external_id', '')}")
                st.markdown(hit.get("chunk_content", ""))

                # 全文表示もsession_stateで保持
                full_key = f"full_text_{i}"
                if st.button("全文を見る", key=f"full_{i}"):
                    doc_id = hit.get("document_id", "")
                    if doc_id:
                        retriever = get_retriever()
                        st.session_state[full_key] = retriever.get_full_document_text(doc_id)

                if full_key in st.session_state:
                    st.markdown(st.session_state[full_key])
    else:
        st.info("該当する結果がありませんでした。")
