"""テンプレートページ"""
from pathlib import Path

import streamlit as st

from src.config import config

st.set_page_config(page_title="テンプレート", page_icon="📋", layout="wide")
st.title("📋 テンプレート管理")

templates_dir = Path(config.templates_path)

if not templates_dir.exists():
    st.warning(f"テンプレートディレクトリが見つかりません: {templates_dir}")
    st.stop()

template_files = sorted(templates_dir.glob("*.md"))

if not template_files:
    st.info("テンプレートが登録されていません。data/templates/ にMarkdownファイルを配置してください。")
    st.stop()

# テンプレート一覧
st.markdown("### テンプレート一覧")

selected = st.selectbox(
    "テンプレートを選択",
    [f.stem for f in template_files],
)

# プレビュー
if selected:
    path = templates_dir / f"{selected}.md"
    content = path.read_text(encoding="utf-8")

    st.markdown(f"### プレビュー: {selected}.md")

    tab1, tab2 = st.tabs(["プレビュー", "Markdown"])
    with tab1:
        st.markdown(content)
    with tab2:
        st.code(content, language="markdown")

    st.download_button(
        "ダウンロード",
        data=content,
        file_name=f"{selected}.md",
        mime="text/markdown",
    )
