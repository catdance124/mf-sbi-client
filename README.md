# mf-sbi-client

[マネーフォワード for 住信SBIネット銀行](https://ssnb.x.moneyforward.com/) の非公式クライアントライブラリ + CLI。

自分のアカウントの入出金明細・口座残高・資産推移を取得し、連携口座の更新(再集計)を実行できます。
ランタイムは httpx + BeautifulSoup のみで、ブラウザは使いません。

## セットアップ

```sh
uv sync
cp .env.example .env   # MF_SBI_EMAIL / MF_SBI_PASSWORD を記入
```

## CLI

`uv run mf-sbi <グループ> <コマンド>` で実行します。グループはサービスの機能区分に対応し、
詳細は `uv run mf-sbi <グループ> --help` で確認できます。

### 参照系(読み取りのみ)

参照系はすべて `--json` で JSON 出力できます(`auth login-check` を除く)。

```sh
# 認証
uv run mf-sbi auth login-check               # ログイン確認(セッションをキャッシュ)

# 連携口座
uv run mf-sbi account list                   # 一覧・残高
uv run mf-sbi account show <account_id>      # 口座別詳細(サマリ・内訳・明細)

# 家計簿
uv run mf-sbi cf transactions                # 入出金明細(既定: 当月)
uv run mf-sbi cf transactions --month 2026-05
uv run mf-sbi cf transactions --from 2026-04 --to 2026-06 --json
uv run mf-sbi cf monthly                     # 月次収支リスト(カテゴリ別 × 月別)
uv run mf-sbi cf summary                     # 支出内訳(カテゴリ別の金額と割合)
uv run mf-sbi cf summary --month 2026-05
uv run mf-sbi cf categories                  # カテゴリ一覧(cf add 用の ID 確認)

# 資産
uv run mf-sbi asset list                     # 資産クラスごとの内訳
uv run mf-sbi asset history                  # 推移(直近日次+月次サマリ)
uv run mf-sbi asset history --month 2026-06  # 指定月の日次全日分
uv run mf-sbi asset history --csv asset_history.csv    # CSV 保存(UTF-8 変換)
uv run mf-sbi asset history --month 2026-06 --csv -    # 指定月の日次 CSV を標準出力へ

# 分析
uv run mf-sbi analysis report                # 月次レポート(既定: 最新月)
uv run mf-sbi analysis report --month 2026-05
uv run mf-sbi analysis diagnosis             # 家計診断(理想の家計との比較、既定: 最新月)
uv run mf-sbi analysis diagnosis --month 2026-05
```

### 書き込み系
`--dry-run` を付けると実行せず内容確認のみ

```sh
# 家計簿
uv run mf-sbi cf add --amount 500 --content コーヒー --large-id 11 --middle-id 43
uv run mf-sbi cf add --amount 500 --dry-run              # 登録内容の確認のみ
uv run mf-sbi cf memo <transaction_id> "メモ"             # 明細メモの更新(20 文字まで)
uv run mf-sbi cf delete <transaction_id>                 # 手入力明細の削除

# 連携口座
uv run mf-sbi account refresh                            # 全口座を口座別更新
uv run mf-sbi account refresh --dry-run                  # 対象口座の確認のみ
uv run mf-sbi account refresh --account-id <ID> --wait   # 単一口座の更新+完了待ち
```

- 「月」はサービス側のユーザー設定の締め日起点の期間です(例: 25日始まりなら
  `--month 2026-05` は 05/25〜06/24)。
- 書き込み系の実行・dry-run はいずれも `logs/audit-YYYY-MM.log` に監査記録が残ります。

## ライブラリとして使う

```python
from datetime import date

from mf_sbi_client import Config, open_client

with open_client(Config.from_env()) as client:
    client.ensure_login()
    accounts = client.list_accounts()
    txs = client.list_transactions(date(2026, 6, 1))
    portfolio = client.get_portfolio()
    history = client.get_asset_history()
```

金額等はサービスの表示文字列を原文のまま保持します(`*_yen` フィールドに数値化済みの値
が入る場合のみ利用可)。アプリ固有の変換は利用側で行ってください。

## セッションキャッシュ

ログイン後の Cookie は `.session/cookies.json`(パーミッション 600)に保存され、
有効な間は再ログインしません。認証切れは自動で検出し、一度だけ再ログインして再試行します。

ログインが何らかの理由(CAPTCHA 導入など)で自動化できなくなった場合は、ブラウザで
ログインした際の Cookie(`_moneybook_session`)を同ファイルの形式
(`[{"name", "value", "domain", "path"}]`)で手動配置すれば以降は動作します。

## 開発

- 品質ゲート: `uv run ruff check src && uv run ruff format --check src && uv run mypy src`
- 各操作のエンドポイント仕様(観測結果)は `docs/specs/` を参照
- 開発規約は `CLAUDE.md` を参照

