# CLI / API インターフェース仕様書

## 1. CLI コマンド一覧

本システムはユーザー操作を最小限にする設計。主要な操作は以下の2つ:
- `python sync.py` — ナレッジの取り込み・同期
- `python generate.py "タイトル"` — 手順書の生成

### 1.1 同期CLI (sync.py) — メインの取り込み手段

```bash
# 基本操作（これだけでOK）
python sync.py

# ファイル変更を常時監視
python sync.py --watch

# 整合性チェック（変更はしない）
python sync.py --check

# 詳細表示
python sync.py --dry-run
```

**引数なし実行の動作**:
1. `data/knowledge/` 配下の全 `.md` ファイルを走査
2. フォルダ構造から source_type / source_system を自動判定
3. ファイル名から external_id を自動生成
4. ファイル内の `# 見出し` からタイトルを自動抽出
5. 新規 → 取り込み / 更新 → 再取り込み / 削除 → 連動削除

| オプション | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `--watch` | flag | No | - | ファイル変更を常時監視する（Ctrl+Cで停止） |
| `--check` | flag | No | - | 整合性チェックのみ実行する（変更はしない） |
| `--dry-run` | flag | No | - | 実行予定の操作を表示するが、実際には変更しない |
| `--init-schema` | flag | No | - | 初回のみ: DBスキーマを適用してから同期する |

**出力例**:
```
[sync] data/knowledge/ を走査中...
[add]    procedure/confluence/server_setup.md → "サーバー構築手順" (5 chunks)
[update] procedure/confluence/backup_config.md → "バックアップ設定手順" (8 chunks)
[skip]   procedure/internal/deploy_flow.md (変更なし)
[delete] ticket/jira/JIRA-789.md → DB + ChromaDB から削除
[sync] 完了: 追加 1, 更新 1, スキップ 1, 削除 1
```

### 1.2 生成CLI (generate.py) — 手順書の自動生成

```bash
# 最小操作（タイトルだけ）
python generate.py "Proxmox バックアップ手順"

# ファイルに保存
python generate.py "Proxmox バックアップ手順" -o output/backup.md

# テンプレート指定
python generate.py "Proxmox バックアップ手順" --template storage

# 詳細指定
python generate.py "K8s Pod再起動手順" \
    --description "CrashLoopBackOffのPodを安全に再起動する" \
    --context "対象: production, namespace=app" \
    --template k8s \
    -o output/k8s_restart.md
```

| 引数/オプション | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `title` | positional | Yes | - | 生成する手順書のタイトル |
| `--description`, `-d` | string | No | タイトルから自動推定 | 手順の詳細説明 |
| `--template`, `-t` | string | No | タイトルから自動選定 | テンプレート名 |
| `--context`, `-c` | string | No | - | 追加コンテキスト（対象サーバー等） |
| `--output`, `-o` | string | No | stdout | 出力ファイルパス |
| `--max-references` | int | No | 3 | 参照する過去手順の最大数 |
| `--list-templates` | flag | No | - | テンプレート一覧を表示して終了 |

**テンプレート自動選定ロジック**:
1. タイトルに含まれるキーワードとテンプレート名を照合
2. 例: "K8s" → `k8s.md`, "ネットワーク" → `network.md`
3. 該当なし → `default.md` を使用

**出力**:
- `-o` 指定時: ファイルに保存、stderrに進捗表示
- `-o` 省略時: stdoutにMarkdown出力
- TODO項目が含まれる場合、stderrに警告を表示

### 1.3 単体取り込みCLI (ingest_cli.py) — 高度な操作用

通常は `sync.py` を使う。個別に細かく制御したい場合のみ使用する。

```
python -m scripts.ingest_cli [OPTIONS]
```

| オプション | 型 | 必須 | 説明 |
|---|---|---|---|
| `--path` | string | Yes | 取り込むファイルのパス |
| `--source-type` | enum | Yes | `procedure` / `ticket` / `config` / `log` |
| `--source-system` | string | Yes | 出元システム名 |
| `--external-id` | string | Yes | 元システムでのID |
| `--title` | string | Yes | ドキュメントのタイトル |
| `--metadata` | JSON string | No | 追加メタデータ（デフォルト: `{}`） |
| `--ticket-fields` | JSON string | No | チケット固有フィールド |
| `--init-schema` | flag | No | 実行前にDBスキーマを適用する |

**出力**: JSON形式
```json
{
  "document_id": "uuid",
  "action": "created | updated | skip",
  "chunks": 5
}
```

## 2. ユーザー操作フローまとめ

### 初回セットアップ（1回だけ）
```bash
pip install -r requirements.txt
cp .env.example .env          # GOOGLE_API_KEY を設定
python sync.py --init-schema  # DB初期化 + 初回同期
```

### 日常操作: ナレッジ追加
```bash
# 1. ファイルを置く
cp my_procedure.md data/knowledge/procedure/confluence/

# 2. 同期
python sync.py
```

### 日常操作: 手順書生成
```bash
python generate.py "やりたいことのタイトル"
```

## 3. 終了コード

全CLI共通:

| コード | 意味 |
|---|---|
| 0 | 正常終了 |
| 1 | エラー（ファイル不在、DB接続エラー、LLM APIエラー等） |

## 4. 将来の Web API 仕様 (Phase 2)

### 4.1 エンドポイント一覧

| Method | Path | 説明 |
|---|---|---|
| POST | `/api/v1/generate` | 手順書生成 |
| POST | `/api/v1/sync` | ナレッジ同期実行 |
| GET | `/api/v1/search` | ナレッジ検索 |
| GET | `/api/v1/templates` | テンプレート一覧 |
| GET | `/api/v1/templates/{name}` | テンプレート内容取得 |
| GET | `/api/v1/documents` | ドキュメント一覧 |
| GET | `/api/v1/documents/{id}` | ドキュメント詳細 |
| GET | `/api/v1/health` | ヘルスチェック |

### 4.2 POST /api/v1/generate

**Request**:
```json
{
  "title": "Proxmox バックアップ手順",
  "description": "全VMを日次バックアップする手順（省略可）",
  "template": "default（省略可、自動選定）",
  "max_references": 3,
  "context": "対象: pve-node01"
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

### 4.3 GET /api/v1/search

**クエリパラメータ**:
| パラメータ | 型 | 必須 | 説明 |
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

## 5. エラーレスポンス形式（Web API）

```json
{
  "status": "error",
  "error": {
    "code": "TEMPLATE_NOT_FOUND",
    "message": "テンプレート 'xxx' が data/templates/ に見つかりません"
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
