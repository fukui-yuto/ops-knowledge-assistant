# CLI / API インターフェース仕様書

## 1. CLI コマンド一覧

### 1.1 取り込みCLI (ingest_cli.py)

```
python -m scripts.ingest_cli [OPTIONS]
```

| オプション | 型 | 必須 | 説明 |
|---|---|---|---|
| `--path` | string | Yes | 取り込むファイルのパス |
| `--source-type` | enum | Yes | `procedure` / `ticket` / `config` / `log` |
| `--source-system` | string | Yes | 出元システム名（confluence, jira, proxmox 等） |
| `--external-id` | string | Yes | 元システムでのID（PROC-001, JIRA-123 等） |
| `--title` | string | Yes | ドキュメントのタイトル |
| `--metadata` | JSON string | No | 追加メタデータ（デフォルト: `{}`） |
| `--ticket-fields` | JSON string | No | チケット固有フィールド（source-type=ticket 時のみ） |
| `--init-schema` | flag | No | 実行前にDBスキーマを適用する |

**出力**: JSON形式
```json
{
  "document_id": "uuid",
  "action": "created | updated | skip",
  "chunks": 5
}
```

**終了コード**:
| コード | 意味 |
|---|---|
| 0 | 正常終了 |
| 1 | エラー（ファイル不在、DB接続エラー等） |

### 1.2 生成CLI (generate_cli.py)

```
python -m scripts.generate_cli [OPTIONS]
```

| オプション | 型 | 必須 | 説明 |
|---|---|---|---|
| `--title` | string | Yes* | 生成する手順書のタイトル |
| `--description` | string | Yes* | 何をする手順かの説明 |
| `--template` | string | No | テンプレート名（デフォルト: `default`） |
| `--max-references` | int | No | 参照する過去手順の最大数（デフォルト: 3） |
| `--extra-context` | string | No | 追加コンテキスト |
| `--output` | string | No | 出力ファイルパス（省略時はstdout） |
| `--list-templates` | flag | No | テンプレート一覧を表示して終了 |

*`--list-templates` 使用時は不要

**出力**:
- `--output` 指定時: ファイルに保存、stderrに進捗表示
- `--output` 省略時: stdoutにMarkdown出力

**終了コード**:
| コード | 意味 |
|---|---|
| 0 | 正常終了 |
| 1 | エラー（テンプレート不在、LLM API エラー等） |

### 1.3 同期CLI (sync_cli.py)

```
python -m scripts.sync_cli [OPTIONS]
```

| オプション | 型 | 必須 | 説明 |
|---|---|---|---|
| `--dir` | string | Yes* | 同期対象ディレクトリ |
| `--source-type` | enum | Yes* | `procedure` / `ticket` / `config` / `log` |
| `--source-system` | string | Yes* | 出元システム名 |
| `--watch` | flag | No | ファイル変更を監視し続ける（Ctrl+Cで停止） |
| `--check` | flag | No | 整合性チェックのみ実行（変更はしない） |
| `--dry-run` | flag | No | 実際には変更せず、実行予定の操作を表示する |
| `--delete-orphans` | flag | No | DB にあるがファイルが存在しないドキュメントを削除する |

*`--check` のみの場合は不要

**動作**:
1. 指定ディレクトリ内の `.md` ファイルを走査
2. 各ファイルについて:
   - DB未登録 → 新規取り込み（external_id はファイル名から生成）
   - DB登録済み＆ハッシュ不一致 → 更新取り込み
   - DB登録済み＆ハッシュ一致 → スキップ
3. `--delete-orphans` 時: DB にあるがディレクトリにないファイル → 削除

**出力例**:
```
[sync] Scanning: procedures/
[add]  new_server_setup.md → PROC-new_server_setup (5 chunks)
[update] backup_procedure.md → PROC-backup_procedure (8 chunks)
[skip] existing_procedure.md (unchanged)
[delete] old_procedure.md → removed from DB + ChromaDB
[sync] Done: 1 added, 1 updated, 1 skipped, 1 deleted
```

## 2. 将来の Web API 仕様 (Phase 2)

### 2.1 エンドポイント一覧

| Method | Path | 説明 |
|---|---|---|
| POST | `/api/v1/ingest` | ファイル取り込み |
| POST | `/api/v1/generate` | 手順書生成 |
| GET | `/api/v1/search` | ナレッジ検索 |
| GET | `/api/v1/templates` | テンプレート一覧 |
| GET | `/api/v1/templates/{name}` | テンプレート内容取得 |
| GET | `/api/v1/documents` | ドキュメント一覧 |
| GET | `/api/v1/documents/{id}` | ドキュメント詳細 |
| GET | `/api/v1/health` | ヘルスチェック |

### 2.2 POST /api/v1/generate

**Request**:
```json
{
  "title": "Proxmox バックアップ手順",
  "description": "全VMを日次バックアップする手順",
  "template": "default",
  "max_references": 3,
  "extra_context": "対象: pve-node01"
}
```

**Response** (200):
```json
{
  "status": "success",
  "content": "# Proxmox バックアップ手順\n\n## 概要\n...",
  "metadata": {
    "template_used": "default",
    "references": [
      {"document_id": "uuid", "title": "...", "similarity": 0.85}
    ],
    "generated_at": "2026-04-28T10:00:00Z",
    "model": "gemini-2.0-flash",
    "has_todos": true
  }
}
```

### 2.3 POST /api/v1/ingest

**Request** (multipart/form-data):
| Field | Type | Required | Description |
|---|---|---|---|
| file | file | Yes | Markdown file |
| source_type | string | Yes | procedure / ticket / config / log |
| source_system | string | Yes | Source system name |
| external_id | string | Yes | External ID |
| title | string | Yes | Document title |
| metadata | JSON string | No | Additional metadata |
| ticket_fields | JSON string | No | Ticket-specific fields |

**Response** (200):
```json
{
  "status": "success",
  "document_id": "uuid",
  "action": "created",
  "chunks": 5
}
```

### 2.4 GET /api/v1/search

**Query Parameters**:
| Param | Type | Required | Description |
|---|---|---|---|
| q | string | Yes | 検索クエリ |
| source_type | string | No | フィルタ: source_type |
| source_system | string | No | フィルタ: source_system |
| limit | int | No | 結果数（デフォルト: 5, 最大: 20） |

**Response** (200):
```json
{
  "status": "success",
  "results": [
    {
      "document_id": "uuid",
      "title": "...",
      "chunk_content": "...",
      "similarity": 0.92,
      "source_type": "procedure",
      "source_system": "confluence"
    }
  ]
}
```

## 3. エラーレスポンス形式

全エンドポイント共通:
```json
{
  "status": "error",
  "error": {
    "code": "TEMPLATE_NOT_FOUND",
    "message": "Template 'xxx' not found in data/templates/"
  }
}
```

| エラーコード | HTTP Status | 説明 |
|---|---|---|
| VALIDATION_ERROR | 400 | リクエストパラメータ不正 |
| TEMPLATE_NOT_FOUND | 404 | テンプレートが存在しない |
| DOCUMENT_NOT_FOUND | 404 | ドキュメントが存在しない |
| LLM_API_ERROR | 502 | Gemini API 呼び出し失敗 |
| DB_ERROR | 500 | PostgreSQL 接続/クエリ失敗 |
| VECTOR_DB_ERROR | 500 | ChromaDB 操作失敗 |
