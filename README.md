# Log Diagnosis Assistant - Data Layer

RAG+Agent システムのデータ基盤。手順生成・問い合わせ回答用のナレッジを管理する。

## アーキテクチャ

```
[原本] data/raw/         (LocalStorage, 後でMinIO/S3に差し替え可)
[メタ] PostgreSQL        documents / chunks / tickets / ingestion_log
[ベクトル] ChromaDB      collection: procedures, tickets, configs, logs
```

3層を `document_id` (UUID) でJOINする。Chromaのmetadataには
`document_id` と検索フィルタに使う属性のみを持たせる。

## セットアップ

```bash
# 依存
pip install -r requirements.txt

# PostgreSQL起動 (Docker例)
docker run -d --name pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 \
    -v $(pwd)/pgdata:/var/lib/postgresql/data postgres:16

# 環境変数
cp .env.example .env
# GOOGLE_API_KEY を設定

# スキーマ適用 + 初回取り込み
export $(cat .env | xargs)
python -m scripts.ingest_cli --init-schema \
    --path data/sample/proc.md \
    --source-type procedure \
    --source-system confluence \
    --external-id PROC-001 \
    --title "Proxmox ノード追加手順"
```

## チケット取り込み例

```bash
python -m scripts.ingest_cli \
    --path data/sample/ticket-123.md \
    --source-type ticket \
    --source-system jira \
    --external-id JIRA-123 \
    --title "K8s Pod が CrashLoopBackOff" \
    --metadata '{"system":"kubernetes","severity":"high"}' \
    --ticket-fields '{"status":"resolved","severity":"high","affected_system":"kubernetes","resolved_at":"2026-04-10T12:00:00","resolution":"resource limit を増加して解消"}'
```

## 設計判断のポイント

| 項目 | 採用 | 理由 |
|---|---|---|
| 原本を別管理 | LocalStorage | ベクトルDBは原本保存に向かない。再Embeddingに必須 |
| chunksをPostgresに保存 | あり | Chromaが壊れても再構築可能、検索後の全文取得が高速 |
| Collection分離 | source_type 単位 | 用途別フィルタで検索精度向上 |
| content_hash | SHA256 | 差分検知。未変更ファイルはスキップ |
| document_id 共有 | UUID | Postgres ⇔ Chroma の結合キー |

## ディレクトリ

```
log_assistant/
├── sql/schema.sql              # DDL
├── src/
│   ├── config.py               # 設定
│   ├── storage.py              # 原本ストレージ抽象
│   ├── db.py                   # Postgresアクセス
│   ├── vector_store.py         # ChromaDBラッパー
│   ├── chunking.py             # チャンク戦略(種別ごと)
│   ├── embedding.py            # Gemini Embedding
│   └── ingestion.py            # 取り込みパイプライン本体
├── scripts/ingest_cli.py       # CLI
├── data/raw/                   # 原本格納
└── requirements.txt
```

## 次のステップ

1. ディレクトリ一括取り込み(`ingest_dir.py`)
2. JIRA / Confluence APIからの自動同期
3. 検索層 (`retriever.py`): hybrid search + re-ranking
4. LangGraph Agent 層
