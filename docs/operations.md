# 運用ガイド

本ドキュメントは ops-knowledge-assistant の日常運用・保守向けガイドです。
初回セットアップは [setup-guide.md](setup-guide.md) を参照してください。

---

## 1. 日常運用

### 1.1 ナレッジの追加・更新・削除

ファイルを `data/knowledge/` に配置・更新・削除するだけです。

**GUI（Streamlit）起動中の場合**: watchdog がファイル変更を自動検知し、3秒後に同期を実行します。手動操作は不要です。

**手動で同期する場合**:
```bash
uv run python sync.py
```

- **追加**: 新しいファイルを置く → 自動同期（または手動 sync.py）→ DB + ChromaDB に自動登録
- **更新**: ファイルを上書き → 自動同期 → content_hash で変更検知、再取り込み
- **削除**: ファイルを消す → 自動同期 → DB + ChromaDB から自動削除（stale data 防止）

事前に変更内容を確認したい場合:
```bash
uv run python sync.py --dry-run
```

### 1.2 手順書の生成

```bash
# タイトルだけで生成（最小操作）
uv run python generate.py "PostgreSQL バックアップ手順"

# ファイルに保存
uv run python generate.py "PostgreSQL バックアップ手順" -o output/backup.md

# 詳細指定
uv run python generate.py "K8s Pod再起動手順" \
    -d "CrashLoopBackOffのPodを安全に再起動する" \
    -t k8s \
    -c "対象: production, namespace=app" \
    -o output/k8s_restart.md
```

### 1.3 整合性チェック

PostgreSQL と ChromaDB の状態を確認:

```bash
uv run python sync.py --check
```

GUI の「設定」ページからも確認可能です。

### 1.4 ヘルスチェック

全コンポーネント（PostgreSQL、ChromaDB、API Key）の状態を一括確認:

```bash
uv run python healthcheck.py
```

出力例:
```
[OK] PostgreSQL
[OK] ChromaDB
[OK] GOOGLE_API_KEY
```

Docker Compose 環境ではコンテナの HEALTHCHECK として自動実行されます。

---

## 2. トラブルシューティング

### 2.1 DB接続エラー

```
psycopg2.OperationalError: could not connect to server
```

**対処**:
1. PostgreSQL が起動しているか確認: `docker ps | grep pg` または `docker compose ps`
2. 停止していた場合: `docker start pg` または `docker compose up -d`
3. `.env` の `PG_HOST`, `PG_PORT` が正しいか確認
4. ファイアウォールで 5432 ポートが開いているか確認

### 2.2 LLM API エラー

**Gemini の場合**:
```
google.api_core.exceptions.PermissionDenied: 403
```

**対処**:
1. `.env` の `GOOGLE_API_KEY` が設定されているか確認
2. APIキーが有効か Google AI Studio で確認
3. Gemini API が有効化されているか確認

**OpenAI の場合**:
```
openai.AuthenticationError: 401
```

**対処**:
1. `.env` の `OPENAI_API_KEY` が設定されているか確認
2. APIキーが有効か OpenAI Platform で確認
3. `LLM_PROVIDER=openai` が設定されているか確認

### 2.3 ChromaDB エラー

```
chromadb.errors.ChromaError
```

**対処**:
1. `data/chroma/` ディレクトリの権限を確認
2. 破損した場合は `data/chroma/` を削除し、`uv run python sync.py` で再構築
3. GUI の設定ページ →「ベクトル再構築」をクリック

### 2.4 生成結果にTODOが多い

**原因**: 過去手順のナレッジが不足している
**対処**:
1. 関連する過去手順を追加で取り込む
2. 追加情報（`-c` / GUI の詳細オプション）で具体的な情報を与える
3. `--max-references` の値を増やす

### 2.5 ファイルを更新したのに反映されない

`uv run python sync.py` を実行してください。ファイルの `content_hash`（SHA256）で変更を検知し、変更があったファイルだけ再取り込みします。

---

## 3. バックアップ

### 3.1 PostgreSQL

```bash
# バックアップ
docker exec pg pg_dump -U postgres log_assistant > backup_$(date +%Y%m%d).sql

# Docker Compose環境の場合
docker compose exec postgres pg_dump -U postgres log_assistant > backup_$(date +%Y%m%d).sql

# リストア
docker exec -i pg psql -U postgres log_assistant < backup_20260428.sql
```

### 3.2 原本ファイル

```bash
# data/raw/ をバックアップ
tar czf raw_backup_$(date +%Y%m%d).tar.gz data/raw/
```

### 3.3 ChromaDB

ChromaDB は PostgreSQL の chunks テーブルから再構築可能なため、バックアップ必須ではない。
`data/chroma/` を削除して `uv run python sync.py` で再構築可能。

---

## 4. 監視

### 4.1 ヘルスチェック

`healthcheck.py` で全コンポーネントの状態を確認できます。
Docker Compose 環境では 30秒間隔で自動実行されます。

```bash
uv run python healthcheck.py
```

### 4.2 監視項目

| 項目 | 確認方法 | 閾値 |
|---|---|---|
| PostgreSQL 接続 | `healthcheck.py` / `docker compose ps` | 応答なし → アラート |
| ChromaDB ヘルス | `healthcheck.py` | エラー → アラート |
| LLM API | `healthcheck.py` | キー未設定 → アラート |
| ディスク使用量 | `df -h` / `docker system df` | 80%超 → 警告 |
| 取り込みエラー率 | `sync.py --check` / GUI 設定ページ | エラー頻発 → 警告 |

### 4.3 ログ確認

```bash
# Docker Compose環境のログ
docker compose logs -f app
docker compose logs -f postgres

# 取り込み履歴はDB内の ingestion_log テーブルに記録
# 生成履歴はDB内の generation_log テーブルに記録
```

---

## 5. Docker Compose

### 5.1 構成

```yaml
services:
  postgres:    # PostgreSQL 16 (メタデータ + チャンク保存)
  app:         # Streamlit アプリ (GUI + 全機能)
```

### 5.2 起動・停止

```bash
# 起動（初回はビルドも自動実行）
docker compose up -d

# 初回のみ: DBスキーマ初期化
docker compose exec app uv run python sync.py --init-schema

# 停止
docker compose down

# 停止 + データ削除（完全リセット）
docker compose down -v
```

### 5.3 ポート変更

`.env` で `APP_PORT` を変更:
```
APP_PORT=8502
```

### 5.4 ナレッジの同期（Docker Compose環境）

`data/knowledge/` はホスト側からマウントされるので、ホスト側でファイルを置いた後:

```bash
docker compose exec app uv run python sync.py
```

またはGUIの「ナレッジ管理」からアップロードも可能。

### 5.5 ビルドし直す場合

```bash
docker compose build --no-cache
docker compose up -d
```

---

## 6. 環境変数一覧

| 変数名 | デフォルト | 説明 |
|---|---|---|
| PG_HOST | localhost | PostgreSQL ホスト |
| PG_PORT | 5432 | PostgreSQL ポート |
| PG_DB | log_assistant | PostgreSQL データベース名 |
| PG_USER | postgres | PostgreSQL ユーザー |
| PG_PASSWORD | postgres | PostgreSQL パスワード |
| CHROMA_PATH | ./data/chroma | ChromaDB 永続化パス |
| RAW_STORAGE_PATH | ./data/raw | 原本ファイル保存パス |
| KNOWLEDGE_PATH | ./data/knowledge | ナレッジディレクトリパス |
| TEMPLATES_PATH | ./data/templates | テンプレートディレクトリパス |
| LLM_PROVIDER | gemini | LLMプロバイダ（`gemini` または `openai`） |
| GOOGLE_API_KEY | (gemini時必須) | Google Gemini API キー |
| EMBEDDING_MODEL | models/gemini-embedding-001 | Gemini Embedding モデル名 |
| GENERATION_MODEL | gemini-2.5-flash-lite | Gemini 生成モデル名 |
| OPENAI_API_KEY | (openai時必須) | OpenAI API キー |
| OPENAI_EMBEDDING_MODEL | text-embedding-3-small | OpenAI Embedding モデル名 |
| OPENAI_GENERATION_MODEL | gpt-4o-mini | OpenAI 生成モデル名 |
| CHUNK_SIZE | 800 | チャンクサイズ（文字数） |
| CHUNK_OVERLAP | 100 | チャンクオーバーラップ（文字数） |
| APP_PORT | 8502 | Streamlit アプリのポート（Docker Compose用） |
