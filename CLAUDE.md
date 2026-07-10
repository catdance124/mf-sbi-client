# mf-sbi-client 開発規約

マネーフォワード for 住信SBIネット銀行(https://ssnb.x.moneyforward.com/)の非公式クライアントライブラリ + CLI。
公開 API がないため、実トラフィックを観測して HTTP を再現する。

## 基本方針

- ランタイムは **httpx + BeautifulSoup + python-dotenv のみ**。Playwright はランタイム依存に含めない
  (開発時に Playwright MCP で通信を観測する用途に限る)。
- **観測ファースト**: 新しい操作を実装する前に、必ず Playwright MCP で実際の通信を観測し、
  エンドポイント・パラメータ・トークン・レスポンス形を `docs/specs/<domain>/<op>.md` に記録する。
- URL・リクエスト整形・解析ロジックは `http_client.py` と `_domains/` に閉じ込める。
  CLI や利用側コードに生 HTTP を書かない。新しい操作は該当ドメイン Mixin のメソッドとして追加する。
- 公開 API は `__init__.py` に集約する。新しいモデル・例外・定数は必ず `__all__` に再輸出する。
  CLI の `main` は再輸出しない。

## セキュリティ・安全性

- 資格情報のハードコード禁止。環境変数(.env、gitignore 済み)から読む。
- 破壊的・不可逆な操作(連携口座の更新実行など)は dry-run 既定 + 監査ログ(`logs/audit-YYYY-MM.log`)必須。
- パスワード・Cookie 値をログ・監査ログに出力しない。
- 開発中は読み取り専用の操作を優先する。

## ツール・品質

- パッケージ管理は **uv 専用**(pip / venv 直叩き禁止)。`uv sync` / `uv run`。
- 品質ゲート: `uv run ruff check src && uv run ruff format --check src && uv run mypy src`。
  テストスイートは持たない(実機検証 + docs/specs が代替)。
- コメント・docstring・コミットメッセージ・Issue/PR はすべて日本語。
- 解析失敗時の例外メッセージには「未ログインまたは仕様変更の可能性」の趣旨を含める。

## リリース

- semver の git タグ `vX.Y.Z` + CHANGELOG.md 更新。
- `main` へ直接コミットしない。ブランチ → PR → squash マージ。
