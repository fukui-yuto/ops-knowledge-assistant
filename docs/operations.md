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
```

### 1.4 初回同期（DB初期化 + ナレッジ取り込み）

```bash
# data/knowledge/ にファイルを配置してから:
python sync.py --init-schema
```

### 1.5 Docker Compose (将来)

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
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data

volumes:
  pgdata:
```

## 2. 日常運用

### 2.1 GUI で操作する場合（推奨）

```bash
# GUI起動
streamlit run app.py
```

ブラウザで http://localhost:8501 を開き、以下の操作をGUIだけで行える:
- ナレッジ管理: ファイルのアップロード・閲覧・削除
- 手順書生成: タイトル入力 → 生成 → コピー/ダウンロード
- テンプレート: 一覧・プレビュー
- 検索: ナレッジの横断検索
- 設定: 状態確認・整合性チェック

詳細は [docs/gui-spec.md](gui-spec.md) を参照。

### 2.2 CLI で操作する場合

#### ナレッジの取り込み（ファイルを置いて同期）

```bash
# 1. ファイルを所定フォルダに配置
cp my_procedure.md data/knowledge/procedure/confluence/

# 2. 同期実行（これだけ）
python sync.py
```

#### 手順書の生成

```bash
# タイトルだけで生成（最小操作）
python generate.py "Proxmox バックアップ手順"

# ファイルに保存
python generate.py "Proxmox バックアップ手順" -o output/backup.md

# 詳細指定
python generate.py "K8s Pod再起動手順" \
    -d "CrashLoopBackOffのPodを安全に再起動する" \
    -t k8s \
    -c "対象: production, namespace=app" \
    -o output/k8s_restart.md
```

#### テンプレート管理

```bash
# テンプレート追加（ファイルを置くだけ）
cp my_template.md data/templates/k8s.md

# テンプレート一覧確認
python generate.py --list-templates
```

### 2.3 ナレッジディレクトリの構造

```
data/knowledge/
├── procedure/              # 手順書
│   ├── confluence/         # 出元システム
│   │   ├── server_setup.md
│   │   └── backup_config.md
│   └── internal/
│       └── deploy_flow.md
├── ticket/                 # チケット
│   └── jira/
│       └── JIRA-123.md
├── config/                 # 設定情報
│   └── proxmox/
│       └── cluster_config.md
└── log/                    # ログパターン
    └── app/
        └── error_patterns.md
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
3. GUI の設定ページ →「ベクトル再構築」をクリック

### 3.4 生成結果にTODOが多い

**原因**: 過去手順のナレッジが不足している
**対処**:
1. 関連する過去手順を追加で取り込む
2. 追加情報（`--context` / GUI の詳細オプション）で具体的な情報を与える
3. 参照数を増やす

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
GUI の設定ページまたは将来の `rebuild_vectors` スクリプトで再構築可能。

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
| KNOWLEDGE_PATH | ./data/knowledge | ナレッジディレクトリパス |
| EMBEDDING_MODEL | models/text-embedding-004 | Embedding モデル名 |
| GOOGLE_API_KEY | (必須) | Google Gemini API キー |
| CHUNK_SIZE | 800 | チャンクサイズ（文字数） |
| CHUNK_OVERLAP | 100 | チャンクオーバーラップ（文字数） |
