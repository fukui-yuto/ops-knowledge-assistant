# ops-knowledge-assistant

テンプレート手順書と過去の運用手順をナレッジベースに取り込み、新規手順書をLLMで自動生成するシステム。
Web GUI またはコマンドライン、どちらからでも操作可能。

## 仕組み

```
1. テンプレート手順書を配置      → data/templates/
2. 過去手順をフォルダに置く      → data/knowledge/procedure/confluence/ 等
3. 同期（GUIアップロード or sync.py）→ PostgreSQL + ChromaDB に自動取り込み
4. 手順書タイトルを入力          → LLMがテンプレ + 過去手順を参考に自動生成
```

## クイックスタート

```bash
# セットアップ
pip install -r requirements.txt
cp .env.example .env          # GOOGLE_API_KEY を設定

# GUI で使う場合（推奨）
streamlit run app.py          # ブラウザで http://localhost:8501

# CLI で使う場合
python sync.py --init-schema  # 初回: DB初期化 + ナレッジ同期
python generate.py "Proxmox バックアップ手順"
```

## GUI で操作（コマンド不要）

`streamlit run app.py` でブラウザから全操作が可能:

| 画面 | できること |
|---|---|
| 手順書生成 | タイトルを入力 → 生成 → コピー/ダウンロード |
| ナレッジ管理 | ファイルのアップロード・閲覧・削除 |
| テンプレート | テンプレートの一覧・プレビュー |
| 検索 | ナレッジベースの横断検索 |
| 設定 | 接続状態確認・整合性チェック・DB初期化 |

## CLI で操作

### ナレッジの取り込み

```bash
# ファイルを置いて同期（これだけ）
cp my_procedure.md data/knowledge/procedure/confluence/
python sync.py
```

フォルダ構造から source_type / source_system を自動判定。
ファイル内の `# 見出し` からタイトルを自動抽出。

### 手順書の生成

```bash
# タイトルだけで生成（最小操作）
python generate.py "Proxmox バックアップ手順"

# ファイルに保存
python generate.py "Proxmox バックアップ手順" -o output/backup.md

# 詳細指定
python generate.py "K8s Pod再起動手順" \
    -d "CrashLoopBackOffのPodを安全に再起動" \
    -t k8s \
    -c "対象: production" \
    -o output/k8s_restart.md
```

## ナレッジディレクトリ構造

```
data/knowledge/
├── procedure/confluence/server_setup.md
├── procedure/internal/deploy_flow.md
├── ticket/jira/JIRA-123.md
├── config/proxmox/cluster_config.md
└── log/app/error_patterns.md
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

## アーキテクチャ

```
[テンプレート] data/templates/     テンプレート手順書(Markdown)
[ナレッジ]    data/knowledge/      ユーザーがここにファイルを置く
[原本]        data/raw/            取り込み済みファイル(LocalStorage)
[メタDB]      PostgreSQL           documents / chunks / tickets
[ベクトルDB]  ChromaDB             collection: procedures, tickets, configs, logs
[生成]        Gemini 2.0 Flash     テンプレ + 過去手順 + 指示 → 新規手順書
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
| テンプレート自動選定 | タイトルキーワード照合 | 指定不要で最適なテンプレートを使用 |
| GUI | Streamlit | Pythonのみ、コマンド不要で全操作可能 |
| データ自動同期 | 追加/削除時に全ストア連動 | staleデータを防止、整合性を保証 |
