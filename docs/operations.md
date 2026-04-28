# 運用ガイド

## 1. 環境構築

### 1.1 前提条件

- Python 3.11+
- PostgreSQL 16+
- Google Cloud アカウント（Gemini API Key）

### 1.2 初回セットアップ

```bash
# リポジトリクローン
git clone https://github.com/fukui-yuto/ops-knowledge-assistant.git
cd ops-knowledge-assistant

# Python仮想環境
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows

# 依存パッケージ
pip install -r requirements.txt

# 環境変数
cp .env.example .env
# .env を編集して GOOGLE_API_KEY を設定
```

### 1.3 PostgreSQL セットアップ

```bash
# Docker で起動
docker run -d --name pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=log_assistant \
  -p 5432:5432 \
  -v $(pwd)/pgdata:/var/lib/postgresql/data \
  postgres:16

# スキーマ適用
python -m scripts.ingest_cli --init-schema \
    --path /dev/null --source-type procedure \
    --source-system init --external-id INIT-000 \
    --title "init"
```

### 1.4 Docker Compose (将来)

```yaml
# docker-compose.yml (計画)
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: log_assistant
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  app:
    build: .
    depends_on:
      - postgres
    environment:
      PG_HOST: postgres
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    volumes:
      - ./data:/app/data

volumes:
  pgdata:
```

## 2. 日常運用

### 2.1 手順書の取り込み

```bash
# 単一ファイル取り込み
python -m scripts.ingest_cli \
    --path procedures/new_procedure.md \
    --source-type procedure \
    --source-system confluence \
    --external-id PROC-042 \
    --title "新規サーバー構築手順"

# 結果確認
# → {"document_id": "xxx", "action": "created", "chunks": 8}
```

### 2.2 手順書の生成

```bash
# 生成してファイルに保存
python -m scripts.generate_cli \
    --title "Proxmox バックアップ手順" \
    --description "Proxmox VE環境の全VMを日次でPBSにバックアップする設定手順" \
    --template default \
    --output output/proxmox_backup.md

# 生成結果を確認・編集
# output/proxmox_backup.md を開いて TODO 項目を埋める
```

### 2.3 テンプレートの管理

```bash
# テンプレート追加
cp my_template.md data/templates/k8s.md

# テンプレート一覧確認
python -m scripts.generate_cli --list-templates

# 特定テンプレートで生成
python -m scripts.generate_cli \
    --title "..." --description "..." --template k8s
```

## 3. トラブルシューティング

### 3.1 DB接続エラー

```
psycopg2.OperationalError: could not connect to server
```

**対処**:
1. PostgreSQL が起動しているか確認: `docker ps | grep pg`
2. `.env` の `PG_HOST`, `PG_PORT` が正しいか確認
3. ファイアウォールで 5432 ポートが開いているか確認

### 3.2 Gemini API エラー

```
google.api_core.exceptions.PermissionDenied: 403
```

**対処**:
1. `.env` の `GOOGLE_API_KEY` が設定されているか確認
2. APIキーが有効か Google Cloud Console で確認
3. Gemini API が有効化されているか確認

### 3.3 ChromaDB エラー

```
chromadb.errors.ChromaError
```

**対処**:
1. `data/chroma/` ディレクトリの権限を確認
2. 破損した場合は `data/chroma/` を削除し、PostgreSQL chunks から再構築する
   ```bash
   # 再構築スクリプト（将来実装予定）
   python -m scripts.rebuild_vectors
   ```

### 3.4 生成結果にTODOが多い

**原因**: 過去手順のナレッジが不足している
**対処**:
1. 関連する過去手順を追加で取り込む
2. `--extra-context` で具体的な情報を追加する
3. `--max-references` を増やす

## 4. バックアップ

### 4.1 PostgreSQL

```bash
# バックアップ
docker exec pg pg_dump -U postgres log_assistant > backup_$(date +%Y%m%d).sql

# リストア
docker exec -i pg psql -U postgres log_assistant < backup_20260428.sql
```

### 4.2 原本ファイル

```bash
# data/raw/ をバックアップ
tar czf raw_backup_$(date +%Y%m%d).tar.gz data/raw/
```

### 4.3 ChromaDB

ChromaDB は PostgreSQL の chunks テーブルから再構築可能なため、バックアップ必須ではない。
再構築手順は `rebuild_vectors` スクリプトで対応する（将来実装）。

## 5. 監視項目 (将来)

| 項目 | 確認方法 | 閾値 |
|---|---|---|
| PostgreSQL 接続 | SELECT 1 | 応答なし → アラート |
| ChromaDB ヘルス | collection.count() | エラー → アラート |
| Gemini API レスポンス | 生成テスト | 60秒超 → 警告 |
| ディスク使用量 | data/raw/, data/chroma/ | 80%超 → 警告 |
| 取り込みエラー率 | ingestion_log の error 率 | 10%超 → 警告 |

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
| EMBEDDING_MODEL | models/text-embedding-004 | Embedding モデル名 |
| GOOGLE_API_KEY | (必須) | Google Gemini API キー |
| CHUNK_SIZE | 800 | チャンクサイズ（文字数） |
| CHUNK_OVERLAP | 100 | チャンクオーバーラップ（文字数） |
