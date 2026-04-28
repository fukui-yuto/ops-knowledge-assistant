"""ops-knowledge-assistant Web GUI (Streamlit)"""
import streamlit as st

st.set_page_config(
    page_title="ops-knowledge-assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("ops-knowledge-assistant")
st.markdown("テンプレート + 過去手順から新規手順書を自動生成するシステム")
st.markdown("---")
st.markdown("左のサイドバーからページを選択してください。")

st.sidebar.success("ページを選択してください。")
