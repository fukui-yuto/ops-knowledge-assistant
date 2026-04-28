"""手順書生成ページ"""
import streamlit as st

st.set_page_config(page_title="手順書生成", page_icon="📄", layout="wide")
st.title("📄 手順書を生成する")


@st.cache_resource
def get_generator():
    from src.generator import ProcedureGenerator
    return ProcedureGenerator()


try:
    generator = get_generator()
    templates = generator.list_templates()
except Exception as e:
    st.error(f"初期化エラー: {e}")
    st.info("GOOGLE_API_KEY が .env に設定されているか確認してください。")
    st.stop()

# メイン入力
title = st.text_input("タイトル", placeholder="例: Proxmox バックアップ手順")

# 詳細オプション（折りたたみ）
with st.expander("詳細オプション"):
    description = st.text_area("説明（省略可）", placeholder="手順の詳細説明")
    template_options = ["（自動選定）"] + templates
    selected_template = st.selectbox("テンプレート", template_options)
    context = st.text_area("追加情報（省略可）", placeholder="対象サーバー名、制約条件など")
    max_refs = st.slider("参照する過去手順の数", 1, 10, 3)

# 生成ボタン
if st.button("生成する", type="primary", disabled=not title):
    template_name = "" if selected_template == "（自動選定）" else selected_template

    with st.spinner("手順書を生成中..."):
        try:
            result = generator.generate(
                title=title,
                description=description or "",
                template_name=template_name,
                max_references=max_refs,
                extra_context=context or "",
            )
            info = generator.last_generation_info
        except Exception as e:
            st.error(f"生成エラー: {e}")
            st.stop()

    # メタ情報
    col1, col2, col3 = st.columns(3)
    col1.metric("テンプレート", info["template_used"])
    col2.metric("参考手順数", len(info["references"]))
    col3.metric("TODO項目", info["todo_count"])

    if info["todo_count"] > 0:
        st.warning(f"TODO項目が {info['todo_count']} 件あります。確認してください。")

    # 結果表示
    st.markdown("---")
    st.markdown("### 生成結果")

    tab1, tab2 = st.tabs(["プレビュー", "Markdown"])
    with tab1:
        st.markdown(result)
    with tab2:
        st.code(result, language="markdown")

    # アクション
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "ダウンロード (.md)",
            data=result,
            file_name=f"{title.replace(' ', '_')}.md",
            mime="text/markdown",
        )
    with col_b:
        if st.button("クリップボードにコピー"):
            st.code(result, language="markdown")
            st.info("上のコードブロックから手動でコピーしてください。")
