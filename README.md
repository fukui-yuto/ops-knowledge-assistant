# ops-knowledge-assistant

テンプレート手順書と過去の運用手順をナレッジベースに取り込み、新規手順書をLLMで自動生成するシステム。

## 仕組み

```
1. テンプレート手順書を配置      → data/templates/
2. 過去手順・チケットを取り込み   → PostgreSQL + ChromaDB
3. 新規手順の生成を命令          → LLMがテンプレ + 過去手順を参考に自動生成
```

## アーキテクチャ

```
[テンプレート] data/templates/     テンプレート手順書(Markdown)
[原本]        data/raw/            取り込み済みファイル(LocalStorage)
[メタDB]      PostgreSQL           documents / chunks / tickets / ingestion_log
[ベクトルDB]  ChromaDB             collection: procedures, tickets, configs, logs
[生成]        Gemini 2.0 Flash     テンプレ + 過去手順 + 指示 → 新規手順書
```

詳細は [docs/architecture.md](docs/architecture.md) を参照。

## セットアップ

```bash
# 依存パッケージ
pip install -r requirements.txt

# PostgreSQL起動 (Docker例)
docker run -d --name pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=log_assistant \
    -p 5432:5432 -v $(pwd)/pgdata:/var/lib/postgresql/data postgres:16

# 環境変数
cp .env.example .env
# .env を編集して GOOGLE_API_KEY を設定
```

詳細は [docs/operations.md](docs/operations.md) を参照。

## 使い方

### 1. 過去手順の取り込み

```bash
# スキーマ初期化 + 手順書取り込み
python -m scripts.ingest_cli --init-schema \
    --path data/sample/proc.md \
    --source-type procedure \
    --source-system confluence \
    --external-id PROC-001 \
    --title "Proxmox ノード追加手順"

# チケット取り込み
python -m scripts.ingest_cli \
    --path data/sample/ticket-123.md \
    --source-type ticket \
    --source-system jira \
    --external-id JIRA-123 \
    --title "K8s Pod が CrashLoopBackOff" \
    --metadata '{"system":"kubernetes","severity":"high"}' \
    --ticket-fields '{"status":"resolved","severity":"high","affected_system":"kubernetes","resolved_at":"2026-04-10T12:00:00","resolution":"resource limit を増加して解消"}'
```

### 2. 新規手順書の生成

```bash
# テンプレート一覧
python -m scripts.generate_cli --list-templates

# 手順書を生成（stdout出力）
python -m scripts.generate_cli \
    --title "Proxmox バックアップ手順" \
    --description "Proxmox VEの全VMを日次バックアップする手順を作成"

# ファイルに保存
python -m scripts.generate_cli \
    --title "K8s Pod再起動手順" \
    --description "CrashLoopBackOffになったPodを安全に再起動する" \
    --extra-context "対象クラスタはproduction、namespace=app" \
    --output output/k8s_pod_restart.md
```

### 3. ディレクトリ同期（予定）

```bash
# ディレクトリ内のファイルを一括同期
python -m scripts.sync_cli \
    --dir procedures/ \
    --source-type procedure \
    --source-system confluence

# ファイル変更の自動監視
python -m scripts.sync_cli --dir procedures/ --source-type procedure --source-system confluence --watch

# 整合性チェック
python -m scripts.sync_cli --check
```

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [docs/requirements.md](docs/requirements.md) | 要件定義書 |
| [docs/architecture.md](docs/architecture.md) | アーキテクチャ設計書 |
| [docs/template-spec.md](docs/template-spec.md) | テンプレート仕様書 |
| [docs/api-spec.md](docs/api-spec.md) | CLI/API インターフェース仕様書 |
| [docs/data-model.md](docs/data-model.md) | データモデル仕様書 |
| [docs/operations.md](docs/operations.md) | 運用ガイド |

## ディレクトリ構成

```
ops-knowledge-assistant/
├── CLAUDE.md                # Claude Code 指示書
├── README.md                # 本ファイル
├── docs/                    # 設計ドキュメント・仕様書群
├── config.py                # 設定管理（環境変数ベース）
├── db.py                    # PostgreSQL アクセス層
├── vector_store.py          # ChromaDB ラッパー
├── chunking.py              # ソース種別ごとのチャンク戦略
├── embedding.py             # Gemini Embedding
├── storage.py               # 原本ファイルストレージ
├── ingestion.py             # 取り込みパイプライン
├── retriever.py             # ベクトル検索（関連手順取得）
├── generator.py             # LLM手順書生成
├── ingest_cli.py            # 取り込みCLI
├── generate_cli.py          # 生成CLI
├── schema.sql               # PostgreSQL DDL
├── data/
│   ├── templates/           # テンプレート手順書（Git管理）
│   ├── raw/                 # 取り込み済み原本（gitignore）
│   └── chroma/              # ChromaDB永続化（gitignore）
├── requirements.txt
└── .env.example
```

## 設計判断

| 項目 | 採用 | 理由 |
|---|---|---|
| 原本を別管理 | LocalStorage | ベクトルDBは原本保存に向かない。再Embeddingに必須 |
| chunksをPostgresに保存 | あり | Chromaが壊れても再構築可能、検索後の全文取得が高速 |
| Collection分離 | source_type単位 | 用途別フィルタで検索精度向上 |
| content_hash | SHA256 | 差分検知。未変更ファイルはスキップ |
| document_id共有 | UUID | Postgres ⇔ Chroma の結合キー |
| テンプレート | ファイルベース | DB管理不要、直接編集しやすい |
| データ自動同期 | 追加/削除時に全ストア連動 | staleデータを防止、整合性を保証 |
