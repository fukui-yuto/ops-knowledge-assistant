# knowledge/ — ナレッジ配置ディレクトリ

ここにMarkdownファイルを置くだけでナレッジベースに取り込まれます。
GUI（Streamlit）起動中は watchdog が自動検知して同期します。手動の場合は `sync.py` を実行してください。

## ディレクトリ構成

```
knowledge/
├── wiki/                       # Wiki（過去の運用手順書・ナレッジ記事）
│   ├── local/                 # GUIアップロード・ローカル配置用
│   │   ├── server_setup.md
│   │   └── backup_procedure.md
│   └── {repo_name}/           # Gitリポジトリ同期（自動配置）
│       └── deploy_flow.md
└── issue/                      # Issue（障害対応記録・インシデント履歴）
    ├── local/
    │   └── manual_incident.md
    └── {repo_name}/
        └── ISS-001.md
```

## 種別（第1階層）の説明

| ディレクトリ | source_type | 用途 | 例 |
|---|---|---|---|
| `wiki/` | wiki | 過去の運用手順書・ナレッジ記事 | サーバー構築手順、バックアップ手順、デプロイ手順 |
| `issue/` | issue | 障害対応・インシデント記録 | JIRA チケット、障害対応報告書 |

上記2種別以外のディレクトリは無視されます。

## ソース（第2階層）の説明

| ディレクトリ | source_system | 用途 |
|---|---|---|
| `local/` | local | GUIアップロード・手動ファイル配置用 |
| `{repo_name}/` | リポジトリ名 | Gitリポジトリ同期による自動配置 |

## ファイル形式

- Markdown（`.md`）のみ対応
- ファイルの先頭に `# タイトル` を書くとタイトルとして自動抽出
- タイトルがない場合はファイル名がタイトルになる
- ファイル名（拡張子除く）が `external_id` として使用される

## 自動同期の仕組み

- **GUI起動中**: watchdog がファイルの追加・変更・削除を検知し、3秒後に自動同期
- **手動同期**: `uv run python sync.py`（または `docker compose exec app uv run python sync.py`）
- **差分検知**: ファイルの SHA256 ハッシュで変更を検知。未変更ファイルはスキップ
- **リポジトリ同期**: `repo_sync.py` が外部Gitリポジトリから定期的にpull→knowledge/へ配置
