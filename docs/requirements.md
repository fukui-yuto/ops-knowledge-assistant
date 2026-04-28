# 要件定義書

## 1. プロジェクト概要

| 項目 | 内容 |
|---|---|
| プロジェクト名 | ops-knowledge-assistant |
| 目的 | 運用手順書の自動生成による作成工数削減・品質均一化 |
| 対象ユーザー | インフラ運用チーム（SRE / 情シス） |
| 想定規模 | 手順書 100〜500件、チケット 1,000〜10,000件 |

## 2. UX設計方針

**ユーザーの操作は最小限にする。**

### 取り込み（ユーザーがやること）
1. `data/knowledge/{source_type}/` にMarkdownファイルを置く
2. `python sync.py` を実行する（GUI起動中は watchdog が自動同期）

これだけで、ファイル名からexternal_id、ファイル内の `# 見出し` からタイトルを自動抽出し、
フォルダ構造から source_type を自動判定して取り込む。

### 生成（ユーザーがやること）
1. `python generate.py "PostgreSQL バックアップ手順"` を実行する

これだけで、テンプレート自動選定・関連手順自動検索・LLM生成が行われ、手順書が出力される。

## 3. 機能要件

### 3.1 ナレッジ取り込み (Ingestion)

| ID | 要件 | 優先度 |
|---|---|---|
| F-ING-001 | Markdownファイルを単体で取り込める | Must |
| F-ING-002 | ディレクトリ一括取り込み（`python sync.py` 一発）ができる | Must |
| F-ING-003 | 取り込み時にcontent_hashで差分検知し、未変更ファイルはスキップする | Must |
| F-ING-004 | source_type はフォルダ構造から自動判定する（`data/knowledge/{source_type}/`） | Must |
| F-ING-006 | タイトルはファイル内の最初の `# 見出し` から自動抽出する。見出しがなければファイル名を使用する | Must |
| F-ING-007 | external_id はファイル名（拡張子除く）から自動生成する | Must |
| F-ING-008 | チケットには severity / status / affected_system 等の構造化フィールドを保持できる（Markdown frontmatter対応） | Should |
| F-ING-009 | 取り込み履歴を ingestion_log に記録する | Must |
| F-ING-010 | 既存ドキュメント更新時、旧チャンク・ベクトルを自動削除して再取り込みする | Must |
| F-ING-011 | ファイル追加・更新・削除を watchdog で自動検知し取り込み/削除する（GUI起動中） | Must |
| F-ING-012 | ドキュメント削除時、PostgreSQL・ChromaDB・LocalStorageの全データを自動で連動削除する | Must |
| F-ING-013 | 同期状態の整合性チェックコマンドを提供する（DB・ChromaDB・ファイルの不整合検出） | Should |
| F-ING-014 | JIRA API からチケットを自動同期できる | Could |
| F-ING-015 | Confluence API から手順書を自動同期できる | Could |

### 3.2 テンプレート管理

| ID | 要件 | 優先度 |
|---|---|---|
| F-TPL-001 | テンプレートはMarkdownファイルとして `data/templates/` に配置する | Must |
| F-TPL-002 | テンプレートにプレースホルダ（`{{title}}`, `{{system}}` 等）を使用できる | Must |
| F-TPL-003 | 複数テンプレートから用途に応じて選択できる | Must |
| F-TPL-004 | テンプレートを指定しない場合、タイトルからLLMが最適なテンプレートを自動選定する | Must |
| F-TPL-005 | テンプレート一覧をCLIで確認できる | Must |
| F-TPL-006 | テンプレートにカテゴリタグを付与できる（例: network, storage, k8s） | Should |
| F-TPL-007 | テンプレートのバージョン管理はGitで行う | Must |

### 3.3 手順書生成 (Generation)

| ID | 要件 | 優先度 |
|---|---|---|
| F-GEN-001 | タイトルのみで新規手順書をMarkdownで生成できる（最小操作） | Must |
| F-GEN-002 | 説明文（description）はオプション。省略時はタイトルから自動推定する | Must |
| F-GEN-003 | テンプレートの構成（見出し・セクション順）に従って生成する | Must |
| F-GEN-004 | ベクトル検索で関連する過去手順を自動取得し、参考にして生成する | Must |
| F-GEN-005 | 追加コンテキスト（対象サーバー名、制約条件等）を渡せる | Should |
| F-GEN-006 | 使用するテンプレートを指定できる（省略時は自動選定） | Must |
| F-GEN-007 | 参照する過去手順の最大数を指定できる | Should |
| F-GEN-008 | 生成結果をファイル出力またはstdout出力できる | Must |
| F-GEN-009 | 生成履歴（誰が・いつ・何を生成したか）をDBに記録する | Should |
| F-GEN-010 | 生成された手順書に「TODO: 要確認」を含む場合に警告を出す | Should |
| F-GEN-011 | 生成結果をそのまま取り込み（Ingest）してナレッジに追加できる | Could |

### 3.4 検索 (Retrieval)

| ID | 要件 | 優先度 |
|---|---|---|
| F-RET-001 | 自然言語クエリでベクトル類似検索ができる | Must |
| F-RET-002 | source_type でフィルタリングできる | Must |
| F-RET-003 | チャンク単位の検索結果からドキュメント全文を取得できる | Must |
| F-RET-004 | ハイブリッド検索（ベクトル + キーワード）ができる | Could |
| F-RET-005 | 検索結果のリランキングができる | Could |

## 4. 非機能要件

### 4.1 性能

| ID | 要件 | 目標値 |
|---|---|---|
| NF-PERF-001 | 手順書生成のレスポンス時間 | 30秒以内 |
| NF-PERF-002 | ベクトル検索のレスポンス時間 | 2秒以内 |
| NF-PERF-003 | 単一ファイル取り込み時間 | 10秒以内 |
| NF-PERF-004 | 同時利用ユーザー数 | 5人（初期） |

### 4.2 信頼性

| ID | 要件 |
|---|---|
| NF-REL-001 | ChromaDBが破損してもPostgreSQLのchunksから再構築できる |
| NF-REL-002 | LLM API障害時にわかりやすいエラーメッセージを返す |
| NF-REL-003 | 取り込み途中で失敗した場合、部分的なデータが残らない（トランザクション整合性） |

### 4.3 セキュリティ

| ID | 要件 |
|---|---|
| NF-SEC-001 | APIキーは環境変数で管理し、コードやログに含めない |
| NF-SEC-002 | 生成した手順書に機密情報（パスワード等）を含めない指示をプロンプトに含める |
| NF-SEC-003 | DB接続情報は環境変数で管理する |

### 4.4 運用

| ID | 要件 |
|---|---|
| NF-OPS-001 | Docker Compose で全コンポーネントを起動できる |
| NF-OPS-002 | ログはJSON形式で構造化出力する |
| NF-OPS-003 | ヘルスチェックエンドポイントを提供する（Web API化時） |

### 4.5 拡張性

| ID | 要件 |
|---|---|
| NF-EXT-001 | LLMプロバイダを環境変数 `LLM_PROVIDER` で切り替えられる（Gemini / OpenAI） |
| NF-EXT-002 | ストレージバックエンドを差し替えられる（Local → MinIO/S3） |
| NF-EXT-003 | Web UI / Slack Bot 等のフロントエンドを後から追加できる構造にする |

## 5. 制約事項

| 項目 | 制約 |
|---|---|
| LLM | Google Gemini API または OpenAI API（LLM_PROVIDERで切り替え） |
| SDK | google-genai / openai（プロバイダに応じて使用） |
| Embedding | Gemini: gemini-embedding-001(768次元) / OpenAI: text-embedding-3-small(1536次元) |
| DB | PostgreSQL 16+。ローカル or Docker |
| ベクトルDB | ChromaDB（組み込みモード）。大規模時はクライアント/サーバーモードに移行 |
| ファイル形式 | 入力・出力ともMarkdown (.md) |
| 言語 | 手順書は日本語 |

## 6. 用語定義

| 用語 | 定義 |
|---|---|
| テンプレート | 手順書の雛形。セクション構成と記載ルールを定義するMarkdownファイル |
| 過去手順 | 既存の運用手順書。ナレッジベースとして取り込み済みのもの |
| チャンク | ドキュメントを分割した単位。ベクトル検索・LLMコンテキストの基本単位 |
| ナレッジディレクトリ | `data/knowledge/` 配下のフォルダ。ここにファイルを置くだけで取り込み対象になる |
| source_type | ドキュメント種別: wiki / issue |
| Ingestion | ドキュメントの取り込み処理（保存→チャンク→Embedding→DB登録） |
| Generation | テンプレ + 過去手順 + 指示 → LLMで新規手順書を生成する処理 |

## 7. ユースケース

### UC-001: 新規手順書の作成（最小操作）
1. ユーザーが `python generate.py "PostgreSQL バックアップ手順"` を実行する
2. システムがタイトルから最適なテンプレートを自動選定する
3. システムが関連する過去手順をベクトル検索で取得する
4. システムがLLMに（テンプレート + 過去手順 + タイトル）を渡す
5. LLMが新規手順書を生成する
6. stdoutにMarkdownが出力される

### UC-002: 詳細指定で手順書を作成
1. ユーザーが以下を実行する:
   ```
   python generate.py "PostgreSQL バックアップ手順" \
       --description "全DBを日次でバックアップ" \
       --template default \
       --context "対象: db-server01" \
       --output output/pg_backup.md
   ```
2. 指定されたテンプレート・説明・コンテキストに基づいて生成される
3. ファイルに保存される

### UC-003: 過去手順の取り込み（最小操作）
1. ユーザーが `data/knowledge/wiki/` にMarkdownファイルを配置する
2. ユーザーが `python sync.py` を実行する
3. システムがフォルダ構造からメタデータを自動判定し、取り込みを実行する

### UC-004: テンプレートの追加
1. ユーザーが `data/templates/` にMarkdownファイルを配置する
2. 生成時に自動選定されるか、`--template <名前>` で明示指定する

### UC-005: 既存手順書の更新
1. ユーザーが `data/knowledge/` 内のファイルを編集して保存する
2. ユーザーが `python sync.py` を実行する
3. システムが content_hash を比較し変更を検知する
4. 旧チャンク・ベクトルを削除し、新しい内容で再登録する

### UC-006: 手順書の削除
1. ユーザーが `data/knowledge/` 内のファイルを削除する
2. ユーザーが `python sync.py` を実行する
3. システムが削除を検知し、DB・ChromaDB・LocalStorageから連動削除する

## 8. ナレッジディレクトリ規約

ユーザーが手順書を配置するディレクトリの構造（2階層）:

```
data/knowledge/
├── wiki/                   # source_type = wiki（運用手順書・ナレッジ記事）
│   ├── server_setup.md     # external_id = server_setup, タイトルはファイル内#見出しから
│   ├── backup_config.md
│   └── deploy_flow.md
└── issue/                  # source_type = issue（障害対応記録・インシデント履歴）
    ├── JIRA-123.md
    └── disk_full_incident.md
```

将来的に GitLab Wiki / Issues と同期予定のため、種別を wiki / issue に統一している。

### 自動推定ルール

| メタデータ | 推定元 | 例 |
|---|---|---|
| source_type | 第1階層フォルダ名 | `wiki/` → `wiki` |
| external_id | ファイル名（拡張子除く） | `server_setup.md` → `server_setup` |
| title | ファイル内の最初の `# 見出し` | `# サーバー構築手順` → `サーバー構築手順` |
| title (フォールバック) | ファイル名をヒューマンリーダブルに変換 | `server_setup` → `server setup` |
