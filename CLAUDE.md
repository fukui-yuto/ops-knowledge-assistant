# CLAUDE.md - Claude Code プロジェクト指示書

## プロジェクト概要
ops-knowledge-assistant: テンプレート手順書 + 過去手順ナレッジから、新規運用手順書をLLMで自動生成するRAGシステム。
Web GUI（Streamlit）とCLIの両方からコマンド不要で操作可能。

## 技術スタック
- Python 3.11+
- PostgreSQL 16（メタデータ、チャンク保存）
- ChromaDB（ベクトルストア）
- Google Gemini（Embedding: text-embedding-004、生成: gemini-2.0-flash）
- LangChain text-splitters（チャンク分割）
- Streamlit（Web GUI）

## ディレクトリ構成
```
ops-knowledge-assistant/
├── CLAUDE.md                # 本ファイル（Claude Code への指示書）
├── README.md                # プロジェクト概要・使い方
├── docs/                    # 設計ドキュメント・仕様書群
│   ├── requirements.md      # 要件定義書
│   ├── architecture.md      # アーキテクチャ設計書
│   ├── template-spec.md     # テンプレート仕様書
│   ├── api-spec.md          # CLI/API インターフェース仕様書
│   ├── gui-spec.md          # Web GUI 仕様書
│   ├── data-model.md        # データモデル仕様書
│   └── operations.md        # 運用ガイド
├── app.py                   # Streamlit GUI エントリポイント
├── pages/                   # Streamlit ページモジュール
│   ├── 01_generate.py       # 手順書生成ページ
│   ├── 02_knowledge.py      # ナレッジ管理ページ
│   ├── 03_templates.py      # テンプレートページ
│   ├── 04_search.py         # 検索ページ
│   └── 05_settings.py       # 設定ページ
├── config.py                # 設定管理（環境変数ベース）
├── db.py                    # PostgreSQL アクセス層
├── vector_store.py          # ChromaDB ラッパー
├── chunking.py              # ソース種別ごとのチャンク戦略
├── embedding.py             # Gemini Embedding
├── storage.py               # 原本ファイルストレージ（LocalStorage）
├── ingestion.py             # 取り込みパイプライン
├── retriever.py             # ベクトル検索（関連手順取得）
├── generator.py             # LLM手順書生成
├── sync.py                  # ナレッジ同期CLI（メインの取り込み手段）
├── generate.py              # 手順書生成CLI（タイトルだけで生成可能）
├── ingest_cli.py            # 単体取り込みCLI（高度な操作用）
├── schema.sql               # PostgreSQL DDL
├── data/
│   ├── templates/           # テンプレート手順書（Git管理対象）
│   ├── knowledge/           # ナレッジ配置ディレクトリ（ユーザーがここにファイルを置く）
│   │   ├── procedure/{source_system}/*.md
│   │   ├── ticket/{source_system}/*.md
│   │   ├── config/{source_system}/*.md
│   │   └── log/{source_system}/*.md
│   ├── raw/                 # 取り込み済み原本（gitignore）
│   └── chroma/              # ChromaDB 永続化（gitignore）
├── requirements.txt
├── .env.example
└── .gitignore
```

## 開発プロセス（最重要・必ず守ること）

### 仕様書ファースト原則
- **コードを書く前に、必ず仕様書（docs/*.md）を先に追記・修正すること**
- 新機能の追加 → まず docs/requirements.md に要件を追記 → docs/api-spec.md or docs/gui-spec.md にインターフェースを定義 → それからコード実装
- 既存機能の変更 → まず関連する仕様書を修正 → それからコード修正
- バグ修正のみの場合はこの限りではないが、仕様書に影響がある場合は先に修正する
- この原則に違反してコードを先に書いてはならない

### 作業の流れ（必ずこの順序で実施）
1. 仕様書の追記・修正（docs/*.md）
2. README.md / CLAUDE.md の更新（必要な場合）
3. コードの実装・修正
4. コミット＆プッシュ（origin/main）

### コードとドキュメントの同期
- コードと仕様書（docs/*.md、README.md）は常に同期を保つこと
- ファイルの追加・削除・リネーム時 → CLAUDE.md のディレクトリ構成、README.md、関連 docs/*.md を更新
- CLIオプションの追加・削除時 → docs/api-spec.md を更新
- GUI画面の追加・変更時 → docs/gui-spec.md を更新
- DBスキーマ変更時（schema.sql） → docs/data-model.md を更新
- 環境変数の追加・削除時 → docs/operations.md の環境変数一覧と .env.example を更新
- テンプレートの追加・削除時 → docs/template-spec.md のカテゴリ表を更新
- アーキテクチャやデータフローの変更時 → docs/architecture.md を更新
- 機能の追加・削除時 → docs/requirements.md を更新

### データの自動同期
- ドキュメント（手順書・チケット等）の追加・削除時、PostgreSQL・ChromaDB・LocalStorage を自動で連動させる
- 古いデータが残らないようにすること（stale data 禁止）
- 詳細は docs/architecture.md「自動同期メカニズム」セクション参照

### Git運用
- タスク完了後は必ずコミット＆プッシュ（origin/main）する

## コーディング規約
- 言語: Python、docstring・コメントは日本語
- 型ヒント: `from __future__ import annotations` を使用、`str | None` 形式（`Optional[str]` は使わない）
- import順: 標準ライブラリ → サードパーティ → ローカル（空行で区切る）
- 設定: 全て環境変数経由、`config.py` の dataclass で管理
- DB接続: `psycopg2` + コンテキストマネージャ（`get_conn()`）、接続は必ず閉じる
- エラー処理: 明確なメッセージで例外を送出、ingestion_log テーブルに記録
- 文字コード: 常にUTF-8
- Markdownファイル: 日本語で記述

## Gitワークフロー
- ブランチ: `main` のみ（当面）
- コミットメッセージ: 日本語、簡潔に、末尾に `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- タスク完了後は必ずコミット＆プッシュする
- gitignore対象: `.env`, `data/raw/`, `data/chroma/`, `data/knowledge/`, `output/`, `pgdata/`

## 主要な設計判断
- `document_id`（UUID）が PostgreSQL ⇔ ChromaDB の結合キー
- テンプレートはファイルベース（`data/templates/*.md`）、DBには入れない
- ナレッジは `data/knowledge/{source_type}/{source_system}/` に置くだけで自動取り込み
- 原本ファイルはベクトルDBとは別管理（再Embedding のため）
- `content_hash`（SHA256）で差分検知、未変更ファイルはスキップ
- ChromaDB のコレクションは `source_type` 単位で分離（フィルタ検索精度向上）
- 手順書生成は Gemini 2.0 Flash で構造化プロンプト（テンプレ + 関連手順 + ユーザー指示）
- GUI は Streamlit で、コード/コマンド不要でブラウザだけで全操作可能

## テスト（予定）
- pytest を使用
- テスト用DB: `log_assistant_test`（本番DBとは分離）
- LLM/Embedding 呼び出しはモックで単体テスト

## よく使うコマンド
```bash
# GUI起動（推奨）
streamlit run app.py

# ナレッジ同期（CLIの場合）
python sync.py

# 手順書生成（CLIの場合）
python generate.py "タイトル"

# テンプレート一覧
python generate.py --list-templates
```
