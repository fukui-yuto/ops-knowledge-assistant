# ops-knowledge-assistant

テンプレート手順書と過去の運用手順をナレッジベースに取り込み、新規手順書をLLMで自動生成するシステム。
Web GUI またはコマンドライン、どちらからでも操作可能。

## 仕組み

```
1. テンプレート手順書を配置      → data/templates/
2. 過去手順をフォルダに置く      → data/knowledge/{wiki,issue}/{repo_or_local}/
3. 外部Gitリポジトリを登録       → 定期pull + 自動配置（任意）
4. 自動同期（ファイル監視で即時取り込み、GUIアップロードも可）→ PostgreSQL + ChromaDB
5. 手順書タイトルを入力          → LLMがテンプレ + 過去手順を参考に自動生成
```

## クイックスタート

```bash
# セットアップ（uv使用）
uv sync
cp .env.example .env          # LLM_PROVIDER と APIキーを設定

# GUI で使う場合（推奨）
uv run streamlit run app.py --server.port 8502  # ブラウザで http://localhost:8502

# CLI で使う場合
uv run python sync.py --init-schema  # 初回: DB初期化 + ナレッジ同期
uv run python generate.py "PostgreSQL バックアップ手順"

# テスト
uv run pytest tests/ -v
```

## GUI で操作（コマンド不要）

`uv run streamlit run app.py --server.port 8502` でブラウザから全操作が可能:

| 画面 | できること |
|---|---|
| 手順書生成 | タイトルを入力 → 生成 → コピー/ダウンロード |
| ナレッジ管理 | ファイルのアップロード・閲覧・削除 |
| テンプレート | テンプレートのアップロード・削除・プレビュー |
| 検索 | ナレッジベースの横断検索 |
| リポジトリ | 外部Gitリポジトリの登録・同期管理 |
| 設定 | 接続状態確認・整合性チェック・DB初期化 |

## CLI で操作

### ナレッジの取り込み

```bash
# ファイルを置くだけ（GUI起動中はwatchdogが自動検知して同期）
cp my_procedure.md data/knowledge/wiki/local/

# 手動で同期する場合
uv run python sync.py

# 外部Gitリポジトリの同期
uv run python repo_sync.py
```

フォルダ構造から source_type を自動判定。
ファイル内の `# 見出し` からタイトルを自動抽出。
GUI（Streamlit）起動中は watchdog がファイル変更を監視し、自動で同期を実行。

### 手順書の生成

```bash
# タイトルだけで生成（最小操作）
uv run python generate.py "PostgreSQL バックアップ手順"

# ファイルに保存
uv run python generate.py "PostgreSQL バックアップ手順" -o output/backup.md

# 詳細指定
uv run python generate.py "K8s Pod再起動手順" \
    -d "CrashLoopBackOffのPodを安全に再起動" \
    -t k8s \
    -c "対象: production" \
    -o output/k8s_restart.md
```

## ナレッジディレクトリ構造

```
data/knowledge/
├── wiki/                       # 運用手順書・ナレッジ記事
│   ├── local/                 # GUIアップロード・ローカル配置用
│   │   ├── server_setup.md
│   │   └── backup_procedure.md
│   └── {repo_name}/           # Gitリポジトリ同期（自動配置）
│       └── deploy_flow.md
└── issue/                      # 障害対応記録・インシデント履歴
    ├── local/
    │   └── manual_incident.md
    └── {repo_name}/
        └── ISS-001.md
```

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [docs/requirements.md](docs/requirements.md) | 要件定義書 |
| [docs/architecture.md](docs/architecture.md) | アーキテクチャ設計書 |
| [docs/gui-spec.md](docs/gui-spec.md) | Web GUI 仕様書 |
| [docs/api-spec.md](docs/api-spec.md) | CLI/API インターフェース仕様書 |
| [docs/template-spec.md](docs/template-spec.md) | テンプレート仕様書 |
| [docs/data-model.md](docs/data-model.md) | データモデル仕様書 |
| [docs/operations.md](docs/operations.md) | 運用ガイド |
| [docs/setup-guide.md](docs/setup-guide.md) | セットアップ＆利用ガイド |

## アーキテクチャ

```
[テンプレート] data/templates/     テンプレート手順書(Markdown)
[ナレッジ]    data/knowledge/      ユーザーがここにファイルを置く（3階層構造）
[リポジトリ]  data/repos/          外部Gitリポジトリのクローン先
[原本]        data/raw/            取り込み済みファイル(LocalStorage)
[メタDB]      PostgreSQL           documents / chunks / tickets
[ベクトルDB]  ChromaDB             collection: wikis, issues
[生成]        Gemini / OpenAI     テンプレ + 過去手順 + 指示 → 新規手順書
[GUI]         Streamlit            ブラウザで全操作可能
```

詳細は [docs/architecture.md](docs/architecture.md) を参照。

## 設計判断

| 項目 | 採用 | 理由 |
|---|---|---|
| 原本を別管理 | LocalStorage | ベクトルDBは原本保存に向かない。再Embeddingに必須 |
| chunksをPostgresに保存 | あり | Chromaが壊れても再構築可能、検索後の全文取得が高速 |
| Collection分離 | source_type単位 | 用途別フィルタで検索精度向上 |
| メタデータ自動推定 | フォルダ構造 + ファイル内容 | ユーザー入力を最小限にする |
| 3階層ディレクトリ | {type}/{repo_or_local}/*.md | リポジトリ同期と手動配置を共存 |
| Gitリポジトリ同期 | 定期pull + knowledge/へ自動配置 | 複数チームのナレッジを自動収集 |
| テンプレート自動選定 | タイトルキーワード照合 | 指定不要で最適なテンプレートを使用 |
| GUI | Streamlit | Pythonのみ、コマンド不要で全操作可能 |
| データ自動同期 | 追加/削除時に全ストア連動 | staleデータを防止、整合性を保証 |
| ファイル監視 | watchdog でリアルタイム検知 | ファイル配置だけで自動取り込み、CLI不要 |
