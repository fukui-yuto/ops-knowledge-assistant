# アーキテクチャ設計書

## 1. システム全体構成

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / Future Web UI                    │
│  ingest_cli.py    generate_cli.py    (future: FastAPI)   │
└──────┬──────────────────┬───────────────────────────────┘
       │                  │
       v                  v
┌──────────────┐  ┌───────────────┐
│  Ingestion   │  │   Generator   │
│  Pipeline    │  │  (LLM生成)    │
│              │  │               │
│ ingestion.py │  │ generator.py  │
└──┬───┬───┬───┘  └──┬────┬──────┘
   │   │   │         │    │
   │   │   │         │    v
   │   │   │         │  ┌──────────────┐
   │   │   │         └─>│  Retriever   │
   │   │   │            │  (検索層)     │
   │   │   │            │ retriever.py  │
   │   │   │            └──┬────┬──────┘
   │   │   │               │    │
   v   v   v               v    v
┌────┐┌─────┐┌───────┐┌─────┐┌─────────┐
│Raw ││Chunk││Embed  ││VecDB││MetaDB   │
│Store││ing  ││ding   ││     ││         │
│    ││     ││       ││Chrom││Postgres │
│stor-││chunk││embedd-││aDB  ││         │
│age  ││ing  ││ing    ││     ││ db.py   │
│.py  ││.py  ││.py    ││vec- ││         │
│    ││     ││       ││tor_ ││         │
│    ││     ││       ││store││         │
│    ││     ││       ││.py  ││         │
└────┘└─────┘└───────┘└─────┘└─────────┘
```

## 2. コンポーネント一覧

| コンポーネント | ファイル | 責務 | 依存先 |
|---|---|---|---|
| Config | config.py | 環境変数ベースの設定管理 | なし |
| Storage | storage.py | 原本ファイルの保存・読み取り | Config |
| DB | db.py | PostgreSQL CRUD | Config |
| VectorStore | vector_store.py | ChromaDB操作（追加・削除・検索） | Config |
| Chunking | chunking.py | source_typeごとのチャンク分割戦略 | Config |
| Embedding | embedding.py | Gemini Embedding API呼び出し | Config |
| Ingestion | ingestion.py | 取り込みパイプライン統合 | Storage, DB, VectorStore, Chunking, Embedding |
| Retriever | retriever.py | ベクトル検索 + ドキュメント全文取得 | DB, VectorStore, Embedding |
| Generator | generator.py | LLM手順書生成 | Retriever, Config |
| IngestCLI | ingest_cli.py | 取り込みコマンドライン | Ingestion, DB |
| GenerateCLI | generate_cli.py | 生成コマンドライン | Generator |

## 3. データフロー

### 3.1 取り込みフロー (Ingestion)

```
入力ファイル(.md)
  │
  ├─1→ LocalStorage に原本コピー (data/raw/{type}/{system}/{id}.md)
  │
  ├─2→ SHA256 ハッシュ計算 → 既存と比較
  │     ├─ unchanged → skip (ingestion_log に記録)
  │     └─ new/updated → 続行
  │
  ├─3→ PostgreSQL documents テーブルに upsert
  │     (updated の場合は旧 chunks 削除)
  │
  ├─4→ source_type に応じたチャンク分割
  │     ├─ procedure: Markdownヘッダ単位 → 大きければ再分割
  │     ├─ ticket: 1チケット=1チャンク（大きければ分割）
  │     └─ その他: RecursiveCharacterTextSplitter
  │
  ├─5→ Gemini text-embedding-004 でベクトル化
  │
  ├─6→ PostgreSQL chunks テーブルに挿入 (vector_id = UUID)
  │
  └─7→ ChromaDB に追加 (同じ vector_id, metadata付き)
```

### 3.2 生成フロー (Generation)

```
ユーザー入力 (title, description, template_name, extra_context)
  │
  ├─1→ テンプレート読み込み (data/templates/{name}.md)
  │
  ├─2→ クエリ = "{title} {description}" でベクトル検索
  │     └─ ChromaDB procedures コレクションから上位N件取得
  │        └─ document_id で PostgreSQL から全文取得
  │
  ├─3→ プロンプト組み立て
  │     ├─ システムプロンプト（手順書作成の専門家ロール）
  │     ├─ テンプレート（構成の指示）
  │     ├─ 関連過去手順（参考資料）
  │     └─ ユーザー指示（タイトル・説明・追加情報）
  │
  └─4→ Gemini 2.0 Flash で生成 → Markdown出力
```

## 4. データストア設計

### 4.1 PostgreSQL (メタデータ + チャンク本文)

```
documents (1) ──< chunks (N)     ... 1文書に複数チャンク
documents (1) ──  tickets (0..1) ... チケット固有情報
documents (1) ──< ingestion_log  ... 取り込み履歴
```

- 全テーブルのPKは UUID (uuid-ossp)
- document_id が PostgreSQL ⇔ ChromaDB の結合キー
- chunks.vector_id = ChromaDB の ID（同一UUID）

### 4.2 ChromaDB (ベクトルインデックス)

| Collection | 対象 source_type | 距離関数 |
|---|---|---|
| procedures | procedure | cosine |
| tickets | ticket | cosine |
| configs | config | cosine |
| logs | log | cosine |

metadata に格納するフィールド:
- `document_id` (フィルタ・JOIN用)
- `source_type`, `source_system` (フィルタ用)
- `chunk_index` (順序復元用)
- ユーザー定義metadata のうち scalar 型のみ

### 4.3 LocalStorage (原本ファイル)

```
data/raw/
├── procedure/
│   └── confluence/
│       ├── PROC-001.md
│       └── PROC-002.md
├── ticket/
│   └── jira/
│       ├── JIRA-123.md
│       └── JIRA-456.md
└── config/
    └── proxmox/
        └── CFG-001.md
```

## 5. 技術選定理由

| 技術 | 選定理由 | 代替候補 |
|---|---|---|
| PostgreSQL | 信頼性、JSONB対応、チャンク全文保持に適切 | SQLite（小規模なら可） |
| ChromaDB | Python組み込み、セットアップ不要、小〜中規模に最適 | Qdrant, Weaviate（大規模時） |
| Gemini text-embedding-004 | 768次元、日本語対応、コスト効率 | OpenAI text-embedding-3-small |
| Gemini 2.0 Flash | 高速・低コスト、日本語手順書生成に十分な品質 | GPT-4o, Claude（品質重視時） |
| LangChain text-splitters | Markdownヘッダ分割対応、実績あり | 自前実装 |
| psycopg2 | PostgreSQLドライバの標準、安定性 | asyncpg（非同期化時） |

## 6. 自動同期メカニズム

ドキュメントの追加・更新・削除が発生した際、全データストアが自動的に同期される。

### 6.1 同期フロー

```
ファイル変更検知 (sync_cli.py --watch / --sync)
  │
  ├─ 新規ファイル検出 → Ingestion Pipeline → DB + ChromaDB + Storage に追加
  │
  ├─ ファイル更新検出 → content_hash 比較
  │   └─ 変更あり → 旧chunks/vectors削除 → 再取り込み
  │
  └─ ファイル削除検出 → DB documents 削除 (CASCADE)
                       → ChromaDB vectors 削除
                       → LocalStorage ファイル削除
```

### 6.2 同期対象

| 操作 | PostgreSQL | ChromaDB | LocalStorage |
|---|---|---|---|
| ファイル追加 | documents + chunks INSERT | vectors ADD | ファイルコピー |
| ファイル更新 | documents UPDATE, chunks 再作成 | 旧vectors DELETE + 新ADD | ファイル上書き |
| ファイル削除 | documents DELETE (CASCADE) | vectors DELETE | ファイル削除 |

### 6.3 整合性チェック

`sync_cli.py --check` で以下の不整合を検出する:
- PostgreSQL にあるが ChromaDB にない vectors
- ChromaDB にあるが PostgreSQL にない vectors
- PostgreSQL にあるが LocalStorage にないファイル
- LocalStorage にあるが PostgreSQL にないファイル

## 7. 将来の拡張ポイント

### Phase 2: Web API化
```
FastAPI
├── POST /api/ingest       (ファイルアップロード取り込み)
├── POST /api/generate     (手順書生成)
├── GET  /api/search       (ナレッジ検索)
├── GET  /api/templates    (テンプレート一覧)
└── GET  /api/health       (ヘルスチェック)
```

### Phase 3: Agent化
- LangGraph ベースの Agent
- ツール: 検索 / 生成 / 取り込み / 承認依頼
- 対話的に手順書を改善するフロー

### Phase 4: 外部連携
- JIRA / Confluence API 自動同期
- Slack Bot（手順書生成リクエスト・通知）
- PDF / Confluence Wiki 形式へのエクスポート
