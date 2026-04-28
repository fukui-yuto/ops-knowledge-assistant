"""テンプレート管理ページ"""
from pathlib import Path

import streamlit as st

from src.config import config

st.set_page_config(page_title="テンプレート", page_icon="📋", layout="wide")
st.title("📋 テンプレート管理")

templates_dir = Path(config.templates_path)
templates_dir.mkdir(parents=True, exist_ok=True)

# --- アップロードセクション ---
st.markdown("### テンプレート登録")

col_up1, col_up2 = st.columns(2)
with col_up1:
    template_name = st.text_input("テンプレート名", placeholder="例: k8s, network, security")
with col_up2:
    upload_method = st.radio("登録方法", ["ファイルアップロード", "直接入力"], horizontal=True)

if upload_method == "ファイルアップロード":
    uploaded_file = st.file_uploader("Markdownファイルを選択", type=["md"], key="tmpl_upload")
    template_content = None
    if uploaded_file:
        template_content = uploaded_file.read().decode("utf-8")
        if not template_name:
            template_name = Path(uploaded_file.name).stem
else:
    template_content = st.text_area(
        "テンプレート内容 (Markdown)",
        height=300,
        placeholder="# {{title}}\n\n## 概要\n...",
    )

# 上書き確認用のチェックボックス
overwrite = False
if template_name and template_content:
    save_path = templates_dir / f"{template_name}.md"
    if save_path.exists():
        overwrite = st.checkbox(f"既存のテンプレート「{template_name}」を上書きする", key="overwrite_check")

if st.button("登録", disabled=not (template_name and template_content)):
    save_path = templates_dir / f"{template_name}.md"
    if save_path.exists() and not overwrite:
        st.warning(f"テンプレート「{template_name}」は既に存在します。上書きするにはチェックを入れてください。")
    else:
        save_path.write_text(template_content, encoding="utf-8")
        action = "上書き" if save_path.exists() and overwrite else "登録"
        st.success(f"テンプレート「{template_name}」を{action}しました。")
        st.rerun()

# --- 一覧セクション ---
st.markdown("---")
st.markdown("### 登録済みテンプレート一覧")

template_files = sorted(templates_dir.glob("*.md"))

if not template_files:
    st.info("テンプレートが登録されていません。上のフォームからアップロードしてください。")
    st.stop()

selected = st.selectbox(
    "テンプレートを選択",
    [f.stem for f in template_files],
)

if selected:
    path = templates_dir / f"{selected}.md"
    content = path.read_text(encoding="utf-8")

    st.markdown(f"### プレビュー: {selected}.md")

    tab1, tab2 = st.tabs(["プレビュー", "Markdown"])
    with tab1:
        st.markdown(content)
    with tab2:
        st.code(content, language="markdown")

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "ダウンロード",
            data=content,
            file_name=f"{selected}.md",
            mime="text/markdown",
        )
    with col_b:
        if selected != "default":
            if st.button("このテンプレートを削除", key=f"del_tmpl_{selected}"):
                path.unlink()
                st.success(f"テンプレート「{selected}」を削除しました。")
                st.rerun()
        else:
            st.caption("default テンプレートは削除できません")
