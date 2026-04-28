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
    st.info("APIキー（GOOGLE_API_KEY または OPENAI_API_KEY）が .env に設定されているか確認してください。")
    st.stop()

# --- 生成フォーム ---
title = st.text_input("タイトル", placeholder="例: PostgreSQL バックアップ手順")

with st.expander("詳細オプション"):
    description = st.text_area("説明（省略可）", placeholder="手順の詳細説明")
    template_options = ["（自動選定）"] + templates
    selected_template = st.selectbox("テンプレート", template_options)
    context = st.text_area("追加情報（省略可）", placeholder="対象サーバー名、制約条件など")
    max_refs = st.slider("参照する過去手順の数", 1, 10, 3)

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

            # DBに保存
            from src import db
            gen_id = db.save_generation(
                title=title,
                description=description or "",
                template_used=info["template_used"],
                reference_docs=info["references"],
                model=info["model"],
                content=result,
                has_todos=info["todo_count"] > 0,
            )

            st.session_state["generated_result"] = result
            st.session_state["generated_info"] = info
            st.session_state["generated_title"] = title
            st.session_state["generated_id"] = str(gen_id)
        except Exception as e:
            st.error(f"生成エラー: {e}")
            st.stop()

# --- 生成結果の表示（session_stateで保持） ---
if "generated_result" in st.session_state:
    result = st.session_state["generated_result"]
    info = st.session_state["generated_info"]
    gen_title = st.session_state["generated_title"]

    col1, col2, col3 = st.columns(3)
    col1.metric("テンプレート", info["template_used"])
    col2.metric("参考手順数", len(info["references"]))
    col3.metric("TODO項目", info["todo_count"])

    if info["todo_count"] > 0:
        st.warning(f"TODO項目が {info['todo_count']} 件あります。確認してください。")

    st.markdown("---")
    st.markdown("### 生成結果")

    tab1, tab2 = st.tabs(["プレビュー", "Markdown"])
    with tab1:
        st.markdown(result)
    with tab2:
        st.code(result, language="markdown")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.download_button(
            "ダウンロード (.md)",
            data=result,
            file_name=f"{gen_title.replace(' ', '_')}.md",
            mime="text/markdown",
        )
    with col_b:
        if st.button("クリップボードにコピー"):
            st.code(result, language="markdown")
            st.info("上のコードブロックから手動でコピーしてください。")
    with col_c:
        if st.button("結果をクリア"):
            del st.session_state["generated_result"]
            del st.session_state["generated_info"]
            del st.session_state["generated_title"]
            st.session_state.pop("generated_id", None)
            st.rerun()

# --- 生成履歴 ---
st.markdown("---")
st.markdown("### 生成履歴")

try:
    from src import db as db_module
    history = db_module.list_generations(limit=20)

    if history:
        for row in history:
            ts = row["created_at"].strftime("%Y-%m-%d %H:%M") if row["created_at"] else ""
            label = f"{ts} | {row['title']} (テンプレート: {row['template_used']})"

            with st.expander(label):
                col_h1, col_h2 = st.columns([4, 1])
                with col_h1:
                    detail = db_module.get_generation(row["id"])
                    if detail and detail.get("content"):
                        tab_h1, tab_h2 = st.tabs(["プレビュー", "Markdown"])
                        with tab_h1:
                            st.markdown(detail["content"])
                        with tab_h2:
                            st.code(detail["content"], language="markdown")

                        st.download_button(
                            "ダウンロード (.md)",
                            data=detail["content"],
                            file_name=f"{row['title'].replace(' ', '_')}.md",
                            mime="text/markdown",
                            key=f"dl_{row['id']}",
                        )
                    else:
                        st.caption("（本文が保存されていません）")
                with col_h2:
                    if st.button("削除", key=f"del_gen_{row['id']}"):
                        db_module.delete_generation(row["id"])
                        st.success("削除しました")
                        st.rerun()

        st.caption(f"直近 {len(history)} 件を表示")
    else:
        st.info("生成履歴はまだありません。")
except Exception as e:
    st.warning(f"履歴の取得に失敗しました: {e}")
