"""ナレッジQAエンジン。ユーザーの質問に対し、過去ナレッジを検索しLLMが回答を生成する。"""
from __future__ import annotations

import logging
from typing import Any

from .config import config
from .retriever import Retriever

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """\
あなたはインフラ運用ナレッジに基づいて質問に回答する専門家です。
提供された過去のナレッジ（運用手順書・障害対応記録）を参照して、ユーザーの質問に正確に回答してください。

ルール:
- 提供されたナレッジに基づいて回答すること
- ナレッジにない情報を推測で補う場合は「※ナレッジに該当情報なし。一般的な知識に基づく回答です」と明示すること
- コマンド例は実際に使えるものを書くこと
- 回答はMarkdown形式で構造化すること（見出し・リスト・コードブロック等を適切に使用）
- 簡潔かつ正確に回答すること

## 回答例

### 例1
質問: PostgreSQLのバックアップ方法を教えてください

回答:
## PostgreSQL バックアップ手順

参照ナレッジに基づき、以下の手順でバックアップを取得できます。

### 1. pg_dump によるバックアップ
```bash
pg_dump -U postgres -h localhost -d mydb > backup_$(date +%Y%m%d).sql
```

### 2. 確認
```bash
ls -lh backup_*.sql
```

### 注意事項
- 本番環境では `--no-owner` オプションを付けることを推奨
- 大規模DBの場合は `pg_dump -Fc`（カスタム形式）を使用

> 出典: ナレッジ1「PostgreSQL運用手順」

### 例2
質問: アラートが出た場合の初動対応は？

回答:
## アラート発生時の初動対応

### 1. アラート内容の確認
- 対象ホスト・サービスを特定する
- 発生時刻とアラートレベル（Warning/Critical）を確認する

### 2. 影響範囲の確認
- 該当サービスのステータスを確認: `systemctl status <service>`
- ログを確認: `journalctl -u <service> --since "10 minutes ago"`

### 3. エスカレーション判断
- Critical の場合: 即座にチームリーダーへ連絡
- Warning の場合: 15分以内に自動復旧しなければエスカレーション

> 出典: ナレッジ2「障害対応フロー」
"""


def _generate_qa_gemini(system_prompt: str, user_prompt: str, model: str) -> str:
    """Gemini APIでQA回答を生成する。"""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=config.google_api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        ),
    )
    return response.text


def _generate_qa_openai(system_prompt: str, user_prompt: str, model: str) -> str:
    """OpenAI APIでQA回答を生成する。"""
    from openai import OpenAI
    client = OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


class KnowledgeQA:
    """過去ナレッジに基づく質問応答エンジン。"""

    def __init__(self):
        if not config.active_api_key:
            provider = config.llm_provider.upper()
            if provider == "OPENAI":
                raise RuntimeError("OPENAI_API_KEY が設定されていません")
            else:
                raise RuntimeError("GOOGLE_API_KEY が設定されていません")
        self.retriever = Retriever()

    def answer(
        self,
        *,
        question: str,
        source_type_filter: str = "all",
        max_references: int = 5,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """質問に対してナレッジに基づく回答を生成する。

        Returns:
            {
                "answer": str,          # LLMの回答（Markdown）
                "references": [...],    # 参照元ドキュメント情報
            }
        """
        # 1. ベクトル検索で関連ナレッジを取得
        references = self._search_knowledge(
            question, source_type_filter, max_references
        )

        # 2. プロンプト組み立て
        prompt = self._build_prompt(question, references, conversation_history)

        # 3. LLM生成
        model = config.active_generation_model
        if config.llm_provider == "openai":
            answer_text = _generate_qa_openai(QA_SYSTEM_PROMPT, prompt, model)
        else:
            answer_text = _generate_qa_gemini(QA_SYSTEM_PROMPT, prompt, model)

        return {
            "answer": answer_text,
            "references": references,
        }

    def _search_knowledge(
        self,
        question: str,
        source_type_filter: str,
        max_references: int,
    ) -> list[dict[str, Any]]:
        """質問に関連するナレッジをベクトル検索で取得する。"""
        if source_type_filter in ("wiki", "issue"):
            search_types = [source_type_filter]
        else:
            search_types = ["wiki", "issue"]

        all_hits: list[dict[str, Any]] = []
        for stype in search_types:
            try:
                hits = self.retriever.search(
                    question, source_type=stype, n_results=max_references
                )
                all_hits.extend(hits)
            except Exception:
                logger.warning("[qa] %s コレクションの検索に失敗", stype)

        # 距離でソートし、ドキュメント単位で重複排除
        all_hits.sort(key=lambda x: x.get("distance", float("inf")))
        seen: set[str] = set()
        unique_docs: list[dict[str, Any]] = []
        for hit in all_hits:
            doc_id = hit.get("document_id", "")
            if doc_id in seen or not doc_id:
                continue
            seen.add(doc_id)
            full_text = self.retriever.get_full_document_text(doc_id)
            unique_docs.append({
                "document_id": doc_id,
                "title": hit.get("title", ""),
                "source_system": hit.get("source_system", ""),
                "full_text": full_text,
            })
            if len(unique_docs) >= max_references:
                break

        return unique_docs

    def _build_prompt(
        self,
        question: str,
        references: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None,
    ) -> str:
        """LLMに渡すプロンプトを組み立てる。"""
        parts: list[str] = []

        # 関連ナレッジ
        if references:
            parts.append("## 参照ナレッジ")
            for i, ref in enumerate(references, 1):
                parts.append(
                    f"### ナレッジ{i}: {ref['title']} ({ref.get('source_system', '')})\n\n"
                    f"```markdown\n{ref['full_text']}\n```"
                )
        else:
            parts.append("## 参照ナレッジ\n\n（該当するナレッジが見つかりませんでした。）")

        # 会話履歴
        if conversation_history:
            parts.append("## 会話履歴")
            for msg in conversation_history:
                role = "ユーザー" if msg["role"] == "user" else "アシスタント"
                parts.append(f"**{role}**: {msg['content']}")

        # 質問
        parts.append(f"## 質問\n\n{question}")

        # 指示
        parts.append(
            "## 指示\n\n"
            "上記の参照ナレッジに基づいて、質問に回答してください。"
            "回答はMarkdown形式で構造化してください。"
        )

        return "\n\n".join(parts)
