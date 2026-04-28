"""ナレッジQAページ"""
import streamlit as st

st.set_page_config(page_title="質問", page_icon="💬", layout="wide")
st.title("💬 ナレッジQA")


@st.cache_resource
def get_qa():
    from src.qa import KnowledgeQA
    return KnowledgeQA()


# --- 会話履歴の初期化 ---
if "qa_messages" not in st.session_state:
    st.session_state["qa_messages"] = []

# --- 入力エリア ---
source_type_filter = st.selectbox(
    "検索対象", ["全て", "wiki", "issue"], key="qa_filter"
)
filter_value = {"全て": "all", "wiki": "wiki", "issue": "issue"}[source_type_filter]

question = st.chat_input("質問を入力してください...")

if question:
    # ユーザーメッセージを追加
    st.session_state["qa_messages"].append({"role": "user", "content": question})

    try:
        qa = get_qa()

        # 会話履歴（直近10件まで）をLLMに渡す
        history = st.session_state["qa_messages"][:-1][-10:]

        result = qa.answer(
            question=question,
            source_type_filter=filter_value,
            conversation_history=history if history else None,
        )

        # 参照元情報を回答に付加
        refs = result.get("references", [])
        ref_text = ""
        if refs:
            ref_lines = []
            for ref in refs:
                ref_lines.append(
                    f"- {ref['title']} ({ref.get('source_system', '')})"
                )
            ref_text = "\n\n---\n📎 **参照元:**\n" + "\n".join(ref_lines)

        answer_with_refs = result["answer"] + ref_text

        # アシスタントメッセージを追加
        st.session_state["qa_messages"].append({
            "role": "assistant",
            "content": answer_with_refs,
        })

    except Exception as e:
        st.session_state["qa_messages"].append({
            "role": "assistant",
            "content": f"⚠️ エラーが発生しました: {e}",
        })

# --- 会話履歴の表示 ---
for msg in st.session_state["qa_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- クリアボタン ---
if st.session_state["qa_messages"]:
    if st.button("会話をクリア"):
        st.session_state["qa_messages"] = []
        st.rerun()
