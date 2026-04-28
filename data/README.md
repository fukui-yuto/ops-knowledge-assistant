# data/ ディレクトリ構成

本ディレクトリには、アプリケーションが使用する全てのデータが格納されます。

| ディレクトリ | 用途 | Git管理 |
|---|---|---|
| `knowledge/` | ナレッジ配置ディレクトリ（ユーザーがここにファイルを置く） | 対象外（.gitignore） |
| `repos/` | 外部Gitリポジトリのクローン先 | 対象外（.gitignore） |
| `repos.yaml` | リポジトリ同期設定ファイル | 対象外（.gitignore） |
| `raw/` | 取り込み済み原本ファイル（Ingestion Pipeline が自動コピー） | 対象外（.gitignore） |
| `chroma/` | ChromaDB 永続化データ（ベクトルインデックス） | 対象外（.gitignore） |
| `templates/` | テンプレート手順書（手順書生成の雛形） | **Git管理対象** |

## knowledge/ — ナレッジ配置ディレクトリ

ユーザーが手順書やチケット等の Markdown ファイルを配置する場所です。
GUI（Streamlit）起動中は watchdog がファイル変更を自動検知して同期します。

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

**ルール:**
- 第1階層: `wiki`, `issue` のいずれか（それ以外は無視）
- 第2階層: リポジトリ名 or `local`（手動配置用）
- 第3階層: Markdown ファイル（`.md`）
- ファイルの先頭に `# タイトル` を書くとタイトルとして自動抽出される

## repos/ — 外部Gitリポジトリのクローン先

`repos.yaml` に登録された外部Gitリポジトリのクローン先です。
`repo_sync.py` が定期的に git pull を実行し、指定パスのファイルを `knowledge/` に配置します。

```
repos/
├── team-a/                    # リポジトリ名でクローン
│   ├── docs/procedures/*.md
│   └── docs/incidents/*.md
└── team-b/
    └── wiki/*.md
```

## raw/ — 取り込み済み原本

Ingestion Pipeline が `knowledge/` から取り込んだファイルのコピーを保存します。
ChromaDB が破損した場合の再構築元として使用されます。
手動での操作は不要です。

## chroma/ — ChromaDB 永続化

ChromaDB のベクトルインデックスデータが格納されます。
`knowledge/` のファイルから生成された Embedding ベクトルが保存されています。
破損した場合は削除して `sync.py` を再実行すれば再構築できます。

## templates/ — テンプレート手順書

手順書生成の雛形となるテンプレートファイルを配置します。
`default.md` が標準テンプレートとして同梱されています。
詳細は [docs/template-spec.md](../docs/template-spec.md) を参照。
