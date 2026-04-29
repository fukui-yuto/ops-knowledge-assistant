# セットアップ＆利用ガイド

本ドキュメントは ops-knowledge-assistant を初めて使うユーザー向けの手順書です。
環境構築から手順書の自動生成まで、ステップごとに説明します。

日常運用・保守については [operations.md](operations.md) を参照してください。

---

## 目次

1. [前提条件](#1-前提条件)
2. [環境構築](#2-環境構築)
3. [初回セットアップ](#3-初回セットアップ)
4. [動作確認](#4-動作確認)
5. [ナレッジの登録](#5-ナレッジの登録)
6. [手順書の自動生成](#6-手順書の自動生成)
7. [GUI で操作する（推奨）](#7-gui-で操作する推奨)
8. [テンプレートの管理](#8-テンプレートの管理)
9. [コマンド一覧](#9-コマンド一覧)
10. [よくあるトラブル](#10-よくあるトラブル)

---

## 1. 前提条件

### 1.1 必要なソフトウェア

| ソフトウェア | バージョン | 用途 | インストール確認コマンド |
|---|---|---|---|
| Git | 最新 | リポジトリのクローン | `git --version` |
| Docker Desktop | 最新 | PostgreSQL + アプリ実行 | `docker --version` |
| Google Gemini API Key または OpenAI API Key | - | Embedding + 手順書生成 | - |

> **ローカル開発時のみ追加で必要**（Docker Compose を使う場合は不要）:
>
> | ソフトウェア | バージョン | 用途 | インストール確認コマンド |
> |---|---|---|---|
> | Python | 3.11以上 | アプリ実行 | `python --version` |
> | uv | 最新 | Pythonパッケージ管理 | `uv --version` |

### 1.2 Git のインストール

既にインストール済みの場合はスキップしてください。

```bash
# 確認
git --version
# → "git version 2.x.x" と表示されればOK
```

**未インストールの場合**:
- **Windows**: [git-scm.com](https://git-scm.com/download/win) からインストーラをダウンロードして実行
- **Mac**: `brew install git` または Xcode Command Line Tools（`xcode-select --install`）
- **Linux (Ubuntu/Debian)**: `sudo apt install git`

### 1.3 Docker のインストール

既にインストール済みの場合はスキップしてください。

```bash
# 確認
docker --version
# → "Docker version 2x.x.x" と表示されればOK

docker compose version
# → "Docker Compose version v2.x.x" と表示されればOK
```

**未インストールの場合**:

#### Windows / Mac: Docker Desktop

1. [Docker Desktop 公式サイト](https://www.docker.com/products/docker-desktop/) からインストーラをダウンロード
2. インストーラを実行（デフォルト設定のままでOK）
3. インストール完了後、Docker Desktop を起動する
4. **Windows の場合**: 初回起動時に「WSL 2 のインストールが必要」と表示されたら、画面の指示に従ってインストールし、PC を再起動する

> **重要**: Docker Desktop が起動していないと `docker compose` コマンドが使えません。以降の手順を実行する前に、タスクバー（Windows）またはメニューバー（Mac）に Docker のアイコンが表示されていることを確認してください。

#### Linux: Docker Engine + Docker Compose

Linux では Docker Desktop ではなく Docker Engine を直接インストールします。

**Ubuntu / Debian の場合**:
```bash
# 古いバージョンを削除（初回なら不要）
sudo apt-get remove docker docker-engine docker.io containerd runc 2>/dev/null

# 必要なパッケージをインストール
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Docker の公式GPGキーを追加
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# リポジトリを追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker Engine をインストール
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 現在のユーザーを docker グループに追加（sudo なしで実行可能にする）
sudo usermod -aG docker $USER
```

> **重要**: `usermod` の後、一度ログアウトして再ログインしてください（またはターミナルを開き直してください）。これにより `docker` コマンドが `sudo` なしで使えるようになります。

**CentOS / RHEL / Amazon Linux の場合**:
```bash
# 必要なパッケージをインストール
sudo yum install -y yum-utils

# リポジトリを追加
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Docker Engine をインストール
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Docker を起動・自動起動設定
sudo systemctl start docker
sudo systemctl enable docker

# 現在のユーザーを docker グループに追加
sudo usermod -aG docker $USER
```

> ログアウト→再ログイン後、`docker --version` と `docker compose version` で確認してください。

**Linux での起動確認**:
```bash
# Docker デーモンが動いているか確認
sudo systemctl status docker
# → "active (running)" と表示されればOK

# sudo なしで実行できるか確認（再ログイン後）
docker --version
docker compose version
```

### 1.4 API Key の取得

LLM（大規模言語モデル）を使うために、以下のいずれかの API Key が必要です。
**どちらか一方だけあれば動作します**。迷ったら Gemini がおすすめです（無料枠あり）。

#### Google Gemini API Key（推奨）

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. Google アカウントでログイン
3. 左メニュー「Get API key」→「Create API key」をクリック
4. 表示されたキーをコピーして安全な場所に保存（後で `.env` に設定します）

> **注意**: API Key は他人に共有しないでください。漏洩した場合は Google AI Studio で無効化できます。

#### OpenAI API Key

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. アカウントを作成またはログイン
3. 左メニュー「API keys」→「Create new secret key」をクリック
4. 表示されたキー（`sk-` で始まる文字列）をコピーして安全な場所に保存

> **注意**: OpenAI は従量課金制です。事前にクレジットのチャージが必要です。

### 1.5 uv のインストール（ローカル開発時のみ）

Docker Compose を使う場合はこの手順は不要です。

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# pip経由（どの環境でも可）
pip install uv
```

インストール確認:
```bash
uv --version
# → "uv 0.x.x" と表示されればOK
```

---

## 2. 環境構築

### 2.1 リポジトリのクローン

ターミナル（Windows: PowerShell または Git Bash、Mac/Linux: Terminal）を開き、任意のフォルダで以下を実行します。

```bash
git clone https://github.com/fukui-yuto/ops-knowledge-assistant.git
cd ops-knowledge-assistant
```

確認:
```bash
ls data/templates/
# → "default.md" が表示されればOK
```

### 2.2 環境変数の設定

`.env.example` をコピーして `.env` ファイルを作成します。

```bash
# Mac / Linux / Git Bash
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

# Windows コマンドプロンプト
copy .env.example .env
```

`.env` ファイルをテキストエディタ（VSCode、メモ帳など）で開き、API Key を設定します。

**Gemini を使う場合（デフォルト・推奨）**:
```dotenv
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIzaSy...（取得したキーをここに貼り付け）
```

**OpenAI を使う場合**:
```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...（取得したキーをここに貼り付け）
```

> **それ以外の項目はデフォルトのままで動作します。変更は不要です。**
>
> 全環境変数の一覧は [operations.md の環境変数一覧](operations.md#6-環境変数一覧) を参照。

### 2.3 ナレッジディレクトリの作成

クローン直後は `data/knowledge/` 内にサブディレクトリがないため、手動で作成します。

```bash
# Mac / Linux / Git Bash
mkdir -p data/knowledge/wiki/local data/knowledge/issue/local

# Windows PowerShell
New-Item -ItemType Directory -Force -Path data/knowledge/wiki/local, data/knowledge/issue/local

# Windows コマンドプロンプト
mkdir data\knowledge\wiki\local
mkdir data\knowledge\issue\local
```

確認:
```bash
ls data/knowledge/wiki/local
ls data/knowledge/issue/local
# → エラーなく空のディレクトリが表示されればOK
```

> **補足**: このディレクトリにMarkdownファイルを置くことでナレッジとして取り込まれます。詳細は [5. ナレッジの登録](#5-ナレッジの登録) を参照。

### 2.4 Docker Compose で起動

```bash
docker compose up -d
```

初回はDockerイメージのビルドが行われるため、数分かかります（回線速度に依存）。

確認:
```bash
docker compose ps
```

以下のように **両方のサービスが `Up` または `healthy`** と表示されれば成功です:
```
NAME                          STATUS
ops-knowledge-assistant-postgres-1   Up (healthy)
ops-knowledge-assistant-app-1        Up (healthy)
```

> **`app` の STATUS が `Up` だが `healthy` でない場合**: 起動直後は準備中のため、30秒ほど待ってから再度 `docker compose ps` を実行してください。
>
> **エラーが出た場合**: [10. よくあるトラブル](#10-よくあるトラブル) を参照してください。

<details>
<summary>ローカル開発時（Docker を使わず直接実行する場合）</summary>

```bash
# 1. パッケージインストール
uv sync

# 2. PostgreSQLだけDockerで起動
docker compose up -d postgres

# 3. PostgreSQL の起動を確認
docker compose ps
# → postgres が "Up (healthy)" になっていればOK

# 4. アプリをローカル実行
uv run streamlit run app.py --server.port 8502
```

> ローカル開発時は `.env` の `PG_HOST=localhost` のままでOKです（Docker Compose 環境では自動的に上書きされます）。

</details>

---

## 3. 初回セットアップ

データベースのテーブルを作成します。**初回のみ必要** な手順です。

```bash
docker compose exec app uv run python sync.py --init-schema
```

以下のように表示されれば成功です:
```
[ok] スキーマを適用しました
[sync] ./data/knowledge を走査中...
[sync] 完了: 追加 0, 更新 0, スキップ 0, 削除 0
```

> `追加 0` は正常です。まだナレッジファイルを置いていないためです。

確認（データベースと ChromaDB の状態を表示）:
```bash
docker compose exec app uv run python sync.py --check
```

```
[check] 整合性チェックを実行中...
  PostgreSQL: 0 documents, 0 chunks
  ChromaDB [wiki]: 0 vectors
  ChromaDB [issue]: 0 vectors
[check] 完了
```

> **ローカル開発時**: `uv run python sync.py --init-schema`

---

## 4. 動作確認

すべてのコンポーネント（PostgreSQL、ChromaDB、API Key）が正しく動作しているか確認します。

```bash
docker compose exec app uv run python healthcheck.py
```

全項目が `[OK]` になれば環境構築は完了です:
```
[OK] PostgreSQL
[OK] ChromaDB
[OK] GOOGLE_API_KEY
```

**`[NG]` が表示された場合**:

| 項目 | 原因 | 対処 |
|---|---|---|
| PostgreSQL | DB が起動していない | `docker compose ps` で postgres の状態を確認 |
| ChromaDB | データディレクトリの問題 | 通常は自動で解決される。解決しない場合は [operations.md](operations.md) 参照 |
| GOOGLE_API_KEY / OPENAI_API_KEY | `.env` にキーが未設定 or 無効 | `.env` を開いて API Key を確認・再設定 |

> **ローカル開発時**: `uv run python healthcheck.py`

---

## 5. ナレッジの登録

### 5.1 ディレクトリにファイルを配置する

`data/knowledge/` の下に、決まったフォルダ構造でMarkdownファイル（`.md`）を置きます。

```
data/knowledge/
├── wiki/                       # 運用手順書・ナレッジ記事
│   ├── local/                  # 手動配置・GUIアップロード用
│   │   ├── server_setup.md
│   │   └── backup_config.md
│   └── {repo_name}/            # Gitリポジトリ同期（自動配置）
│       └── deploy_flow.md
└── issue/                      # 障害対応記録・インシデント履歴
    ├── local/
    │   └── manual_incident.md
    └── {repo_name}/
        └── ISS-001.md
```

**ルール**:
- 1階層目: `wiki`（手順書・ナレッジ）または `issue`（障害対応記録）のいずれか
- 2階層目: `local`（手動配置用）またはリポジトリ名
- 3階層目: Markdown ファイル（`.md`）
- ファイルの先頭に `# タイトル` を書くと、タイトルとして自動抽出されます

**ファイルの例** (`data/knowledge/wiki/local/backup_procedure.md`):
```markdown
# PostgreSQL バックアップ手順

## 概要
PostgreSQL データベースの定期バックアップ手順。

## 手順
### Step 1: バックアップ対象の確認
...
```

### 5.2 同期する

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
[add]    wiki/local/backup_procedure.md → "PostgreSQL バックアップ手順" (3 chunks)
[add]    issue/local/JIRA-123.md → "Pod CrashLoopBackOff" (1 chunks)
[sync] 完了: 追加 2, 更新 0, スキップ 0, 削除 0
```

> **GUI 経由**: ファイルのアップロードは GUI からもできます（[7. GUI で操作する](#7-gui-で操作する推奨) 参照）。

### 5.3 事前確認（dry-run）

実際に取り込む前に、何が処理されるか確認したい場合:

```bash
docker compose exec app uv run python sync.py --dry-run
```

---

## 6. 手順書の自動生成

### 基本（タイトルだけで生成）

```bash
docker compose exec app uv run python generate.py "PostgreSQL バックアップ手順"
```

これだけで:
1. タイトルから最適なテンプレートを自動選定
2. 過去ナレッジからベクトル検索で関連手順を取得
3. テンプレート + 関連手順 + タイトルをもとに LLM が手順書を生成

### ファイルに保存

```bash
docker compose exec app uv run python generate.py "PostgreSQL バックアップ手順" -o output/backup.md
```

> `output/` ディレクトリは Docker コンテナ内に自動作成されます。ホスト側の `output/` フォルダにもマウントされているため、ホストから直接ファイルを確認できます。

### 詳細指定

```bash
docker compose exec app uv run python generate.py "K8s Pod再起動手順" \
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

## 7. GUI で操作する（推奨）

コマンド操作なしで、ブラウザから全機能を利用できます。

### 起動

Docker Compose を使っている場合、`docker compose up -d` で既に起動しています。
ブラウザで **http://localhost:8502** を開いてください。

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
| 質問（QA） | ナレッジに基づいた質問応答（自然言語で質問できる） |
| 設定 | DB接続状態・統計情報・整合性チェック・スキーマ初期化 |
| リポジトリ | 外部Gitリポジトリの登録・同期管理 |

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

## 8. テンプレートの管理

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

## 9. コマンド一覧

### Docker Compose 環境（推奨）

| コマンド | 説明 |
|---|---|
| `docker compose up -d` | 全サービス起動（PostgreSQL + アプリ） |
| `docker compose down` | 全サービス停止 |
| `docker compose ps` | サービスの状態確認 |
| `docker compose logs -f app` | アプリのログをリアルタイム表示 |
| `docker compose exec app uv run python sync.py --init-schema` | DB初期化 + ナレッジ同期（初回のみ） |
| `docker compose exec app uv run python sync.py` | ナレッジ同期 |
| `docker compose exec app uv run python sync.py --dry-run` | 同期の事前確認 |
| `docker compose exec app uv run python sync.py --check` | 整合性チェック |
| `docker compose exec app uv run python generate.py "タイトル"` | 手順書生成 |
| `docker compose exec app uv run python healthcheck.py` | ヘルスチェック |
| `docker compose build --no-cache` | イメージを再ビルド（コード変更時） |

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

## 10. よくあるトラブル

### `docker compose up -d` でエラーになる

**「Docker daemon is not running」と表示される場合**:
- Docker Desktop が起動していません。Docker Desktop アプリを起動してください。

**「port is already allocated」と表示される場合**:
- ポート 5432（PostgreSQL）または 8502（アプリ）が既に使われています。
- 対処: `.env` でポートを変更します。
  ```dotenv
  PG_PORT=5433
  APP_PORT=8503
  ```
  変更後、`docker compose down && docker compose up -d` で再起動してください。

**ビルドが途中で失敗する場合**:
- ネットワーク接続を確認してください（Docker イメージやパッケージのダウンロードが必要です）。
- 再試行: `docker compose build --no-cache && docker compose up -d`

### `--init-schema` でDB接続エラーになる

```
psycopg2.OperationalError: could not connect to server
```

- PostgreSQL が起動完了していない可能性があります。`docker compose ps` で postgres が `healthy` になっているか確認してください。
- `healthy` になるまで 10〜30秒かかる場合があります。少し待ってから再実行してください。

### healthcheck で API Key が NG になる

- `.env` ファイルの API Key が正しく設定されているか確認してください。
- `your-key-here` や `sk-your-key-here` のままになっていませんか？実際のキーに置き換えてください。
- `.env` を変更した場合、Docker Compose 環境では再起動が必要です:
  ```bash
  docker compose down && docker compose up -d
  ```

### GUI（http://localhost:8502）が開けない

- Docker Compose が起動しているか確認: `docker compose ps`
- `app` サービスが `Up` になっているか確認
- 起動直後はアプリの準備に 10〜20秒かかります。少し待ってからリロードしてください。
- ファイアウォールでポート 8502 がブロックされていないか確認

### LLMプロバイダを切り替えたら検索結果がおかしい

Gemini と OpenAI ではベクトルの次元数が異なる（Gemini: 768次元、OpenAI: 1536次元）ため、プロバイダを切り替えた場合は ChromaDB の再構築が必要です。

```bash
# Docker Compose環境
docker compose exec app uv run python sync.py

# または GUI の「設定」ページ → 「ベクトル再構築」ボタン
```

---

## 全体フロー図

```
┌──────────────────────────────────────────────────────┐
│  1. 前提条件の確認                                      │
│     Git / Docker Desktop インストール済み？              │
│     API Key 取得済み？                                  │
│                                                        │
│  2. 環境構築                                           │
│     git clone → .env設定 → ディレクトリ作成             │
│     → docker compose up -d                             │
│                                                        │
│  3. 初回セットアップ                                     │
│     docker compose exec app                            │
│       uv run python sync.py --init-schema              │
│                                                        │
│  4. 動作確認                                            │
│     docker compose exec app                            │
│       uv run python healthcheck.py                     │
│     → 全て [OK] になることを確認                         │
│                                                        │
│  5. ナレッジ登録                                         │
│     data/knowledge/ にファイル配置                        │
│     → docker compose exec app uv run python sync.py    │
│     （または GUI の「ナレッジ管理」からアップロード）       │
│                                                        │
│  6. 手順書生成                                           │
│     GUI http://localhost:8502 の「手順書生成」画面        │
│     （または docker compose exec app                    │
│       uv run python generate.py "タイトル"）            │
│                                                        │
│  7. 日常運用                                             │
│     → operations.md を参照                              │
└──────────────────────────────────────────────────────┘
```
