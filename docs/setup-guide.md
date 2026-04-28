# セットアップ＆利用ガイド

本ドキュメントは ops-knowledge-assistant を初めて使うユーザー向けの手順書です。
環境構築から手順書の自動生成まで、ステップごとに説明します。

日常運用・保守については [operations.md](operations.md) を参照してください。

---

## 目次

1. [前提条件](#1-前提条件)
2. [環境構築](#2-環境構築)
3. [初回セットアップ](#3-初回セットアップ)
4. [ナレッジの登録](#4-ナレッジの登録)
5. [手順書の自動生成](#5-手順書の自動生成)
6. [GUI で操作する（推奨）](#6-gui-で操作する推奨)
7. [テンプレートの管理](#7-テンプレートの管理)
8. [コマンド一覧](#8-コマンド一覧)

---

## 1. 前提条件

| ソフトウェア | バージョン | 用途 |
|---|---|---|
| Docker / Docker Compose | 最新 | PostgreSQL + アプリ実行 |
| uv | 最新 | Pythonパッケージ管理（ローカル開発時） |
| Python | 3.11以上 | ローカル開発時のみ必要 |
| Google Gemini API Key または OpenAI API Key | - | Embedding + 手順書生成（LLM_PROVIDERで選択） |

> **Docker Compose を使う場合**: Python や uv のローカルインストールは不要です。Docker だけで動作します。

### uv のインストール（ローカル開発時のみ）

```bash
# Linux / Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# pip経由（どの環境でも可）
pip install uv
```

### Google Gemini API Key の取得

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. Google アカウントでログイン
3. 左メニュー「Get API key」→「Create API key」をクリック
4. 表示されたキーをコピー（後で `.env` に設定します）

---

## 2. 環境構築

### 2.1 リポジトリのクローン

```bash
git clone https://github.com/fukui-yuto/ops-knowledge-assistant.git
cd ops-knowledge-assistant
```

### 2.2 環境変数の設定

```bash
cp .env.example .env
```

`.env` ファイルを開き、使用するプロバイダに応じてAPIキーを設定してください。

```
# Gemini を使う場合（デフォルト）
LLM_PROVIDER=gemini
GOOGLE_API_KEY=ここに取得したAPIキーを貼り付け

# OpenAI を使う場合
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-ここにAPIキーを貼り付け
```

その他の項目はデフォルトのままで動作します。
全環境変数の一覧は [operations.md の環境変数一覧](operations.md#6-環境変数一覧) を参照。

### 2.3 Docker Compose で起動

```bash
docker compose up -d
```

これだけで以下が自動的に起動します:
- **PostgreSQL 16**: メタデータ + チャンク保存
- **アプリ（Streamlit）**: Web GUI（http://localhost:8502）

確認:
```bash
docker compose ps
# postgres と app の STATUS が両方 "Up" / "healthy" になっていればOK
```

> **ローカル開発時**（Docker を使わず直接実行する場合）:
> ```bash
> uv sync                        # パッケージインストール
> docker compose up -d postgres   # PostgreSQLだけ起動
> uv run streamlit run app.py --server.port 8502  # アプリをローカル実行
> ```

---

## 3. 初回セットアップ

```bash
docker compose exec app uv run python sync.py --init-schema
```

> **ローカル開発時**: `uv run python sync.py --init-schema`

このコマンドで以下が実行されます:
- PostgreSQL にテーブル（documents, chunks, tickets, generation_log, ingestion_log）を作成
- `data/knowledge/` 内のファイルを自動スキャン・取り込み

初回は `data/knowledge/` が空なので、次のステップでナレッジを登録します。

---

## 4. ナレッジの登録

### 4.1 ディレクトリにファイルを配置する

`data/knowledge/` の下に、決まったフォルダ構造でファイルを置きます。

```
data/knowledge/
├── procedure/              # 過去の手順書
│   ├── confluence/         # 出元システム名（自由に命名可能）
│   │   ├── server_setup.md
│   │   └── backup_config.md
│   └── internal/
│       └── deploy_flow.md
├── ticket/                 # 過去のチケット・障害対応記録
│   └── jira/
│       └── JIRA-123.md
├── config/                 # 構成情報
│   └── k8s/
│       └── cluster_config.md
└── log/                    # ログパターン
    └── app/
        └── error_patterns.md
```

**ルール**:
- 1階層目: `procedure`, `ticket`, `config`, `log` のいずれか（種別）
- 2階層目: 出元システム名（confluence, jira, internal 等、自由に命名可能）
- 3階層目: Markdown ファイル（`.md`）
- ファイルの先頭に `# タイトル` を書くと、タイトルとして自動抽出されます

**ファイルの例** (`data/knowledge/procedure/internal/backup_procedure.md`):
```markdown
# PostgreSQL バックアップ手順

## 概要
PostgreSQL データベースの定期バックアップ手順。

## 手順
### Step 1: バックアップ対象の確認
...
```

### 4.2 同期する

**GUI（Streamlit）起動中の場合**: ファイルを配置するだけで watchdog が自動検知して同期します。手動操作は不要です。

**手動で同期する場合**:
```bash
# Docker Compose環境
docker compose exec app uv run python sync.py

# ローカル開発環境
uv run python sync.py
```

出力例:
```
[sync] ./data/knowledge を走査中...
[add]    procedure/internal/backup_procedure.md → "PostgreSQL バックアップ手順" (3 chunks)
[add]    ticket/jira/JIRA-123.md → "Pod CrashLoopBackOff" (1 chunks)
[sync] 完了: 追加 2, 更新 0, スキップ 0, 削除 0
```

> **GUI 経由**: ファイルのアップロードは GUI からもできます（[6. GUI で操作する](#6-gui-で操作する推奨) 参照）。

### 4.3 事前確認（dry-run）

実際に取り込む前に、何が処理されるか確認したい場合:

```bash
uv run python sync.py --dry-run
```

---

## 5. 手順書の自動生成

### 基本（タイトルだけで生成）

```bash
uv run python generate.py "PostgreSQL バックアップ手順"
```

これだけで:
1. タイトルから最適なテンプレートを自動選定
2. 過去ナレッジからベクトル検索で関連手順を取得
3. テンプレート + 関連手順 + タイトルをもとに LLM が手順書を生成

### ファイルに保存

```bash
uv run python generate.py "PostgreSQL バックアップ手順" -o output/backup.md
```

### 詳細指定

```bash
uv run python generate.py "K8s Pod再起動手順" \
    -d "CrashLoopBackOffのPodを安全に再起動する" \
    -t k8s \
    -c "対象: production, namespace=app" \
    -o output/k8s_restart.md
```

| オプション | 説明 |
|---|---|
| `タイトル` (必須) | 生成する手順書のタイトル |
| `-d` | 詳細説明（省略可） |
| `-t` | テンプレート名（省略時は自動選定） |
| `-c` | 追加コンテキスト（環境情報等） |
| `-o` | 出力ファイルパス（省略時は標準出力） |
| `--max-references` | 参照する過去手順の最大数（デフォルト3） |

---

## 6. GUI で操作する（推奨）

コマンド操作なしで、ブラウザから全機能を利用できます。

### 起動

Docker Compose を使っている場合、`docker compose up -d` で既に起動しています。
ブラウザで http://localhost:8502 を開いてください。

ローカル開発時:
```bash
uv run streamlit run app.py --server.port 8502
```

### 画面一覧

| 画面 | できること |
|---|---|
| 手順書生成 | タイトルを入力 → 生成 → プレビュー → コピー/ダウンロード |
| ナレッジ管理 | ファイルのアップロード・一覧表示・削除 |
| テンプレート | テンプレートの一覧・プレビュー |
| 検索 | ナレッジベースの横断検索（ベクトル類似検索） |
| 設定 | DB接続状態・統計情報・整合性チェック・スキーマ初期化 |

### 基本操作フロー

```
1. 「ナレッジ管理」でファイルをアップロード
   └→ DB + ChromaDB に自動登録される

2. 「手順書生成」でタイトルを入力して「生成」ボタン
   └→ 過去ナレッジ参照 + テンプレート適用 → 手順書が生成される

3. 生成結果をプレビューし、「コピー」or「ダウンロード」
```

詳細は [gui-spec.md](gui-spec.md) を参照。

---

## 7. テンプレートの管理

テンプレートは `data/templates/` にMarkdownファイルとして配置します。

### デフォルトテンプレート

`data/templates/default.md` が標準テンプレートとして同梱されています。
セクション構成: 概要 → 前提条件 → 事前確認 → 作業手順 → 作業後確認 → 切り戻し手順 → 備考

### テンプレートの追加

```bash
# ファイルを置くだけ
cp my_template.md data/templates/network.md
```

ファイル名がテンプレート名になります（例: `network.md` → テンプレート名「network」）。

### テンプレートの自動選定

手順書生成時、タイトルのキーワードから最適なテンプレートが自動選定されます。

| テンプレート | 選定キーワード例 |
|---|---|
| k8s | k8s, kubernetes, kubectl, pod, deployment |
| network | ネットワーク, network, firewall, DNS, VLAN |
| default | 上記に該当しない場合 |

`-t` オプションまたは GUI のドロップダウンで明示的に指定することもできます。
詳細は [template-spec.md](template-spec.md) を参照。

---

## 8. コマンド一覧

### Docker Compose 環境（推奨）

| コマンド | 説明 |
|---|---|
| `docker compose up -d` | 全サービス起動（PostgreSQL + アプリ） |
| `docker compose down` | 全サービス停止 |
| `docker compose exec app uv run python sync.py --init-schema` | DB初期化 + ナレッジ同期（初回のみ） |
| `docker compose exec app uv run python sync.py` | ナレッジ同期 |
| `docker compose exec app uv run python sync.py --dry-run` | 同期の事前確認 |
| `docker compose exec app uv run python sync.py --check` | 整合性チェック |
| `docker compose exec app uv run python generate.py "タイトル"` | 手順書生成 |
| `docker compose exec app uv run python healthcheck.py` | ヘルスチェック |

### ローカル開発環境

| コマンド | 説明 |
|---|---|
| `uv sync` | パッケージインストール |
| `uv run python sync.py --init-schema` | DB初期化 + ナレッジ同期（初回のみ） |
| `uv run python sync.py` | ナレッジ同期 |
| `uv run python generate.py "タイトル"` | 手順書生成 |
| `uv run streamlit run app.py --server.port 8502` | GUI起動 |
| `uv run python healthcheck.py` | ヘルスチェック |
| `uv run pytest tests/ -v` | テスト実行 |

---

## 全体フロー図

```
┌──────────────────────────────────────────────────────┐
│  1. 環境構築                                           │
│     .env設定 → docker compose up -d                    │
│                                                        │
│  2. 初回セットアップ                                     │
│     docker compose exec app                            │
│       uv run python sync.py --init-schema              │
│                                                        │
│  3. ナレッジ登録                                         │
│     data/knowledge/ にファイル配置                        │
│     → docker compose exec app uv run python sync.py    │
│     （または GUI の「ナレッジ管理」からアップロード）       │
│                                                        │
│  4. 手順書生成                                           │
│     GUI http://localhost:8502 の「手順書生成」画面        │
│     （または docker compose exec app                    │
│       uv run python generate.py "タイトル"）            │
│                                                        │
│  5. 日常運用                                             │
│     → operations.md を参照                              │
└──────────────────────────────────────────────────────┘
```
