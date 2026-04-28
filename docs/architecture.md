# アーキテクチャ設計書

## 1. システム全体構成

```
┌─────────────────────────────────────────────────────────┐
│                     フロントエンド                        │
│  Web GUI (Streamlit)    CLI (sync.py / generate.py)     │
└──────┬──────────────────────┬───────────────────────────┘
       │                      │
       v                      v
┌──────────────────────────────────────────────────────────┐
│                     コアエンジン                          │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐          │
│  │ Ingestion│  │ Generator │  │   Retriever  │          │
│  │ Pipeline │  │ (LLM生成) │  │  (検索層)    │          │
│  └──┬───┬───┘  └──┬────┬───┘  └──┬────┬─────┘          │
│     │   │         │    │         │    │                  │
│     v   v         v    v         v    v                  │
│  ┌────┐┌─────┐┌───────┐┌───────────┐┌─────────────┐    │
│  │Raw ││Chunk││Embed  ││ VectorStore││  MetaDB     │    │
│  │Stor││ing  ││ding   ││ (ChromaDB) ││ (PostgreSQL)│    │
│  └────┘└─────┘└───────┘└───────────┘└─────────────┘    │
└──────────────────────────────────────────────────────────┘
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
| SyncCLI | sync.py | ナレッジ同期（メイン取り込み手段） | Ingestion, DB |
| GenerateCLI | generate.py | 手順書生成CLI | Generator |
| HealthCheck | healthcheck.py | 全コンポーネントのヘルスチェック | DB, VectorStore, Config |
| Watcher | watcher.py | ナレッジディレクトリのファイル監視・自動同期 | SyncCLI, Config |
| WebGUI | app.py | StreamlitベースのWeb GUI | Generator, Ingestion, Retriever, Watcher |

## 3. データフロー

### 3.1 ナレッジディレクトリ規約

ユーザーが `data/knowledge/` にファイルを置くだけで取り込み対象になる:

```
data/knowledge/
├── procedure/{source_system}/{ファイル名}.md
├── ticket/{source_system}/{ファイル名}.md
├── config/{source_system}/{ファイル名}.md
└── log/{source_system}/{ファイル名}.md
```

メタデータはフォルダ構造とファイル内容から自動推定:
- `source_type` ← 第1階層フォルダ名
- `source_system` ← 第2階層フォルダ名
- `external_id` ← ファイル名（拡張子除く）
- `title` ← ファイル内の最初の `# 見出し`（なければファイル名）

### 3.2 同期フロー (sync.py / 自動同期)

GUI（Streamlit）起動中は watchdog がファイル変更を監視し、変更検知後にデバウンス（3秒）を経て自動同期を実行する。
手動で同期する場合は `uv run python sync.py` を実行する。

```
uv run python sync.py  （または watchdog による自動実行）
  │
  ├─1→ data/knowledge/ 配下を全走査
  │
  ├─2→ 各ファイルについて:
  │     ├─ フォルダ構造から source_type / source_system を判定
  │     ├─ ファイル名から external_id を生成
  │     └─ ファイル内 # 見出しから title を抽出
  │
  ├─3→ DB の documents と照合:
  │     ├─ 未登録 → Ingestion Pipeline で新規取り込み
  │     ├─ 登録済み＆ハッシュ不一致 → 再取り込み（旧データ削除→新規登録）
  │     └─ 登録済み＆ハッシュ一致 → スキップ
  │
  └─4→ DB にあるが knowledge/ に存在しないファイル → 連動削除
        ├─ PostgreSQL: documents DELETE (CASCADE → chunks, tickets)
        ├─ ChromaDB: vectors DELETE
        └─ LocalStorage: raw ファイル削除
```

### 3.3 取り込みフロー (Ingestion Pipeline)

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
  ├─5→ Gemini Embedding (gemini-embedding-001) でベクトル化
  │
  ├─6→ PostgreSQL chunks テーブルに挿入 (vector_id = UUID)
  │
  └─7→ ChromaDB に追加 (同じ vector_id, metadata付き)
```

### 3.4 生成フロー (Generation)

```
ユーザー入力 (title のみでOK)
  │
  ├─1→ テンプレート自動選定（タイトルキーワード → テンプレート名照合）
  │     └─ 該当なし → default.md
  │
  ├─2→ description 未指定時はタイトルをそのまま使用
  │
  ├─3→ クエリ = "{title} {description}" でベクトル検索
  │     └─ ChromaDB procedures コレクションから上位N件取得
  │        └─ document_id で PostgreSQL から全文取得
  │
  ├─4→ プロンプト組み立て
  │     ├─ システムプロンプト（手順書作成の専門家ロール）
  │     ├─ テンプレート（構成の指示）
  │     ├─ 関連過去手順（参考資料）
  │     └─ ユーザー指示（タイトル・説明・追加情報）
  │
  └─5→ Gemini 2.5 Flash Lite で生成 → Markdown出力
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
├── procedure/confluence/PROC-001.md
├── ticket/jira/JIRA-123.md
└── config/k8s/CFG-001.md
```

## 5. 自動同期メカニズム

ドキュメントの追加・更新・削除が発生した際、全データストアが自動的に同期される。

### 5.1 同期対象

| 操作 | PostgreSQL | ChromaDB | LocalStorage |
|---|---|---|---|
| ファイル追加 | documents + chunks INSERT | vectors ADD | ファイルコピー |
| ファイル更新 | documents UPDATE, chunks 再作成 | 旧vectors DELETE + 新ADD | ファイル上書き |
| ファイル削除 | documents DELETE (CASCADE) | vectors DELETE | ファイル削除 |

### 5.2 整合性チェック

`python sync.py --check` で以下の不整合を検出する:
- PostgreSQL にあるが ChromaDB にない vectors
- ChromaDB にあるが PostgreSQL にない vectors
- PostgreSQL にあるが LocalStorage にないファイル
- LocalStorage にあるが PostgreSQL にないファイル

## 6. 技術選定理由

| 技術 | 選定理由 | 代替候補 |
|---|---|---|
| PostgreSQL | 信頼性、JSONB対応、チャンク全文保持に適切 | SQLite（小規模なら可） |
| ChromaDB | Python組み込み、セットアップ不要、小〜中規模に最適 | Qdrant, Weaviate（大規模時） |
| Gemini Embedding (gemini-embedding-001) | 日本語対応、無料枠あり、コスト効率 | OpenAI text-embedding-3-small |
| Gemini 2.5 Flash Lite | 高速・低コスト、無料枠で安定動作、日本語手順書生成に十分な品質 | GPT-4o, Claude（品質重視時） |
| LangChain text-splitters | Markdownヘッダ分割対応、実績あり | 自前実装 |
| psycopg2 | PostgreSQLドライバの標準、安定性 | asyncpg（非同期化時） |
| Streamlit | Pythonのみ、高速プロトタイピング、データ系UI向き | Gradio, FastAPI+React |
| watchdog | ファイル変更のリアルタイム検知、クロスプラットフォーム対応 | inotify直接利用（Linux限定） |
| google-genai | Google公式の最新Python SDK、旧google-generativeaiの後継 | google-generativeai（非推奨） |

## 7. 拡張ロードマップ

以下は今後の拡張として設計を検討している機能です。

### Agent化
- LangGraph ベースの Agent
- ツール: 検索 / 生成 / 取り込み / 承認依頼
- 対話的に手順書を改善するフロー

### 外部連携
- JIRA / Confluence API 自動同期
- Slack Bot（手順書生成リクエスト・通知）
- PDF / Confluence Wiki 形式へのエクスポート

### REST API
- FastAPI ベースの Web API（[api-spec.md](api-spec.md) セクション4 参照）
- 外部システムからの手順書生成・検索呼び出し
