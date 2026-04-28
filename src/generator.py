"""手順書生成エンジン。テンプレート + 過去手順 + ユーザー指示からLLMで新規手順書を生成する。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import google.generativeai as genai

from .config import config
from .retriever import Retriever


SYSTEM_PROMPT = """\
あなたはインフラ運用の手順書作成の専門家です。
ユーザーの指示に従い、提供されたテンプレートと過去の手順書を参考にして、
新しい運用手順書をMarkdown形式で作成してください。

ルール:
- テンプレートの構成（見出し・セクション順）に従うこと
- 過去手順は内容の参考にするが、そのままコピーしないこと
- コマンド例は実際に使えるものを書くこと
- 前提条件・事前確認・切り戻し手順を必ず含めること
- 手順は具体的かつ再現可能な粒度で記述すること
- 不明な箇所は「TODO: 要確認」と明示すること
- パスワードやAPIキー等の機密情報は含めないこと
"""

# テンプレート自動選定用のキーワードマッピング
TEMPLATE_KEYWORDS: dict[str, list[str]] = {
    "k8s": ["k8s", "kubernetes", "kubectl", "pod", "deployment", "helm", "コンテナ"],
    "network": ["ネットワーク", "network", "firewall", "dns", "vlan", "ルーティング", "routing", "switch"],
    "storage": ["ストレージ", "storage", "バックアップ", "backup", "nfs", "ceph", "zfs", "raid"],
    "security": ["セキュリティ", "security", "脆弱性", "インシデント", "不正アクセス", "証明書", "ssl", "tls"],
    "monitoring": ["監視", "monitoring", "アラート", "alert", "grafana", "prometheus", "zabbix"],
    "migration": ["移行", "migration", "マイグレーション", "データ移行", "リプレース"],
    "incident": ["障害", "incident", "復旧", "切り戻し", "ポストモーテム"],
}


class ProcedureGenerator:
    def __init__(self, templates_dir: str | Path | None = None):
        if not config.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY が設定されていません")
        genai.configure(api_key=config.google_api_key)
        self.model = genai.GenerativeModel(
            model_name=config.generation_model,
            system_instruction=SYSTEM_PROMPT,
        )
        self.templates_dir = Path(templates_dir or config.templates_path)
        self.retriever = Retriever()

    def load_template(self, template_name: str = "default") -> str:
        """テンプレートファイルを読み込む。"""
        path = self.templates_dir / f"{template_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"テンプレートが見つかりません: {path}")
        return path.read_text(encoding="utf-8")

    def list_templates(self) -> list[str]:
        """利用可能なテンプレート一覧を返す。"""
        if not self.templates_dir.exists():
            return []
        return sorted(p.stem for p in self.templates_dir.glob("*.md"))

    def auto_select_template(self, title: str) -> str:
        """タイトルからテンプレートを自動選定する。"""
        available = self.list_templates()
        if not available:
            return "default"

        title_lower = title.lower()
        for template_name, keywords in TEMPLATE_KEYWORDS.items():
            if template_name not in available:
                continue
            for kw in keywords:
                if kw.lower() in title_lower:
                    return template_name

        return "default" if "default" in available else available[0]

    def generate(
        self,
        *,
        title: str,
        description: str = "",
        template_name: str = "",
        max_references: int = 3,
        extra_context: str = "",
    ) -> str:
        """
        新規手順書を生成する。

        Args:
            title: 手順書タイトル（必須）
            description: 手順の詳細説明（省略時はタイトルをそのまま使用）
            template_name: テンプレート名（省略時は自動選定）
            max_references: 参照する過去手順の最大数
            extra_context: 追加コンテキスト
        """
        if not description:
            description = title

        if not template_name:
            template_name = self.auto_select_template(title)

        # 1. テンプレート読み込み
        try:
            template = self.load_template(template_name)
        except FileNotFoundError:
            template = self.load_template("default")
            template_name = "default"

        # 2. 関連する過去手順を検索
        query = f"{title} {description}"
        try:
            related_docs = self.retriever.get_related_full_procedures(
                query, max_docs=max_references
            )
        except Exception:
            related_docs = []

        # 3. プロンプト組み立て
        prompt = self._build_prompt(
            title=title,
            description=description,
            template=template,
            related_docs=related_docs,
            extra_context=extra_context,
        )

        # 4. LLM生成
        response = self.model.generate_content(prompt)
        generated = response.text

        # 5. メタ情報保存
        self._todo_count = len(re.findall(r"TODO:", generated))
        self._template_used = template_name
        self._references = [
            {"document_id": d["document_id"], "title": d["title"]}
            for d in related_docs
        ]

        return generated

    @property
    def last_generation_info(self) -> dict[str, Any]:
        """直前の生成のメタ情報を返す。"""
        return {
            "template_used": getattr(self, "_template_used", ""),
            "references": getattr(self, "_references", []),
            "todo_count": getattr(self, "_todo_count", 0),
            "model": config.generation_model,
        }

    def _build_prompt(
        self,
        *,
        title: str,
        description: str,
        template: str,
        related_docs: list[dict[str, Any]],
        extra_context: str,
    ) -> str:
        parts: list[str] = []

        parts.append(f"## 作成依頼\n\nタイトル: {title}\n説明: {description}")

        if extra_context:
            parts.append(f"## 追加情報\n\n{extra_context}")

        parts.append(f"## テンプレート（この構成に従ってください）\n\n```markdown\n{template}\n```")

        if related_docs:
            parts.append("## 参考: 過去の関連手順書")
            for i, doc in enumerate(related_docs, 1):
                parts.append(
                    f"### 参考{i}: {doc['title']} ({doc.get('external_id', 'N/A')})\n\n"
                    f"```markdown\n{doc['full_text']}\n```"
                )
        else:
            parts.append("## 参考: 過去の関連手順書\n\n（該当する過去手順はありませんでした。一般的な知識に基づいて作成してください。）")

        parts.append(
            "## 指示\n\n"
            "上記のテンプレート構成に従い、過去手順を参考にしながら、"
            f"「{title}」の手順書をMarkdown形式で作成してください。"
        )

        return "\n\n".join(parts)
