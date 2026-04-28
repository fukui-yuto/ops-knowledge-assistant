# データモデル仕様書

## 1. ER図

```
┌───────────────────────┐       ┌──────────────────────┐
│      documents        │       │       tickets        │
├───────────────────────┤       ├──────────────────────┤
│ id (PK, UUID)         │──1:1──│ document_id (PK, FK) │
│ source_type           │       │ status               │
│ source_system         │       │ severity             │
│ external_id           │       │ affected_system      │
│ title                 │       │ resolved_at          │
│ file_path             │       │ resolution           │
│ content_hash          │       └──────────────────────┘
│ metadata (JSONB)      │
│ created_at            │       ┌──────────────────────┐
│ updated_at            │       │      chunks          │
│                       │       ├──────────────────────┤
│ UQ(source_system,     │──1:N──│ id (PK, UUID)        │
│    external_id)       │       │ document_id (FK)     │
└───────────┬───────────┘       │ chunk_index          │
            │                   │ content              │
            │                   │ vector_id            │
            │ 1:N               │ token_count          │
            │                   │ created_at           │
┌───────────┴───────────┐       │                      │
│    ingestion_log      │       │ UQ(document_id,      │
├───────────────────────┤       │    chunk_index)      │
│ id (PK, UUID)         │       └──────────────────────┘
│ document_id (FK)      │
│ action                │       ┌──────────────────────┐
│ message               │       │  generation_log      │
│ executed_at           │       ├──────────────────────┤
└───────────────────────┘       │ id (PK, UUID)        │
                                │ title                │
                                │ description          │
                                │ template_used        │
                                │ reference_docs (JSONB)│
                                │ model                │
                                │ content              │
                                │ output_path          │
                                │ has_todos            │
                                │ created_at           │
                                └──────────────────────┘
```

## 2. テーブル定義

### 2.1 documents

ドキュメントマスタ。全ての原本ファイルの親レコード。

| カラム | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| id | UUID | NOT NULL | uuid_generate_v4() | 主キー |
| source_type | TEXT | NOT NULL | - | `procedure` / `ticket` / `config` / `log` |
| source_system | TEXT | NULL | - | 出元システム名 |
| external_id | TEXT | NULL | - | 元システムでのID |
| title | TEXT | NOT NULL | - | ドキュメントタイトル |
| file_path | TEXT | NOT NULL | - | 原本ストレージ内の相対パス |
| content_hash | TEXT | NOT NULL | - | SHA256ハッシュ（差分検知用） |
| metadata | JSONB | NOT NULL | `{}` | 追加メタデータ |
| created_at | TIMESTAMP | NOT NULL | NOW() | 作成日時 |
| updated_at | TIMESTAMP | NOT NULL | NOW() | 更新日時 |

**制約**:
- PK: `id`
- UNIQUE: `(source_system, external_id)`

**インデックス**:
- `idx_documents_source_type` ON `source_type`
- `idx_documents_source_system` ON `source_system`
- `idx_documents_metadata` GIN ON `metadata`

### 2.2 chunks

チャンク管理。ベクトルDB独立に原本チャンクを保持する。

| カラム | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| id | UUID | NOT NULL | uuid_generate_v4() | 主キー |
| document_id | UUID | NOT NULL | - | FK → documents.id |
| chunk_index | INT | NOT NULL | - | 文書内での順序（0始まり） |
| content | TEXT | NOT NULL | - | チャンク本文 |
| vector_id | TEXT | NULL | - | ChromaDB側のID（同一UUID） |
| token_count | INT | NULL | - | トークン数（概算） |
| created_at | TIMESTAMP | NOT NULL | NOW() | 作成日時 |

**制約**:
- PK: `id`
- FK: `document_id` → `documents.id` ON DELETE CASCADE
- UNIQUE: `(document_id, chunk_index)`

### 2.3 tickets

チケット固有情報。documentsを1:1で拡張する。

| カラム | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| document_id | UUID | NOT NULL | - | PK, FK → documents.id |
| status | TEXT | NULL | - | `open` / `resolved` / `closed` |
| severity | TEXT | NULL | - | `critical` / `high` / `medium` / `low` |
| affected_system | TEXT | NULL | - | 影響を受けたシステム |
| resolved_at | TIMESTAMP | NULL | - | 解決日時 |
| resolution | TEXT | NULL | - | 解決方法の本文 |

### 2.4 ingestion_log

取り込みジョブの実行履歴。

| カラム | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| id | UUID | NOT NULL | uuid_generate_v4() | 主キー |
| document_id | UUID | NULL | - | FK → documents.id (SET NULL on delete) |
| action | TEXT | NOT NULL | - | `create` / `update` / `skip` / `error` |
| message | TEXT | NULL | - | 詳細メッセージ |
| executed_at | TIMESTAMP | NOT NULL | NOW() | 実行日時 |

### 2.5 generation_log

手順書生成の実行履歴。

| カラム | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| id | UUID | NOT NULL | uuid_generate_v4() | 主キー |
| title | TEXT | NOT NULL | - | 生成した手順書のタイトル |
| description | TEXT | NOT NULL | - | ユーザーが入力した説明 |
| template_used | TEXT | NOT NULL | - | 使用したテンプレート名 |
| reference_docs | JSONB | NOT NULL | `[]` | 参照した過去手順のリスト |
| model | TEXT | NOT NULL | - | 使用したLLMモデル名 |
| content | TEXT | NOT NULL | `''` | 生成した手順書の本文（履歴再ダウンロード用） |
| output_path | TEXT | NULL | - | 出力ファイルパス |
| has_todos | BOOLEAN | NOT NULL | false | TODO項目を含むか |
| created_at | TIMESTAMP | NOT NULL | NOW() | 生成日時 |

## 3. ChromaDB コレクション

| コレクション名 | source_type | 距離関数 | 次元数 |
|---|---|---|---|
| procedures | procedure | cosine | 768 |
| tickets | ticket | cosine | 768 |
| configs | config | cosine | 768 |
| logs | log | cosine | 768 |

### metadata スキーマ

各ベクトルに付与する metadata:

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| document_id | string | Yes | PostgreSQL documents.id と同一 |
| source_type | string | Yes | ドキュメント種別 |
| source_system | string | Yes | 出元システム |
| chunk_index | int | Yes | チャンクの順番 |
| (user-defined) | string/int/float/bool | No | ユーザー定義metadata |

## 4. ID体系

| ID | 形式 | 生成元 | 用途 |
|---|---|---|---|
| documents.id | UUID v4 | PostgreSQL uuid-ossp | ドキュメント一意識別 |
| chunks.id | UUID v4 | PostgreSQL uuid-ossp | チャンク一意識別 |
| chunks.vector_id | UUID v4 | Python uuid4() | ChromaDB とのJOINキー |
| external_id | 任意文字列 | 外部システム | 元システムでの識別子 |

## 5. データ整合性ルール

| ルール | 実装箇所 |
|---|---|
| documents 削除時、chunks も CASCADE 削除 | DDL (ON DELETE CASCADE) |
| documents 削除時、tickets も CASCADE 削除 | DDL (ON DELETE CASCADE) |
| documents 削除時、ingestion_log.document_id は NULL に | DDL (ON DELETE SET NULL) |
| chunks 更新時、旧 ChromaDB ベクトルも削除 | ingestion.py (delete → re-add) |
| content_hash が同一なら再取り込みスキップ | db.py upsert_document() |
| (source_system, external_id) は一意 | DDL (UNIQUE制約) |
