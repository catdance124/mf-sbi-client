# mf-sbi-client

マネーフォワード for 住信SBIネット銀行(https://ssnb.x.moneyforward.com/)の非公式クライアントライブラリ + CLI。

自分のアカウントの入出金明細・口座残高・資産推移を取得し、連携口座の更新(再集計)を実行できます。
ランタイムは httpx + BeautifulSoup のみで、ブラウザは使いません。

## セットアップ

```sh
uv sync
cp .env.example .env   # MF_SBI_EMAIL / MF_SBI_PASSWORD を記入
```

## CLI

```sh
uv run mf-sbi login-check                # ログイン確認(セッションをキャッシュ)
uv run mf-sbi accounts                   # 連携口座の一覧・残高(--json 可)
uv run mf-sbi account <account_id>       # 口座別詳細(サマリ・内訳・明細、--json 可)
uv run mf-sbi transactions               # 当月の入出金明細
uv run mf-sbi transactions --month 2026-05
uv run mf-sbi transactions --from 2026-04 --to 2026-06 --json
uv run mf-sbi monthly                    # 月次収支リスト(カテゴリ別 × 月別、--json 可)
uv run mf-sbi report                     # 月次レポート(最新月。--month 2026-05 / --json 可)
uv run mf-sbi assets                     # 資産クラスごとの内訳
uv run mf-sbi asset-history              # 資産推移サマリ(直近日次+月次)
uv run mf-sbi asset-history --month 2026-06        # 指定月の日次全日分
uv run mf-sbi asset-history --csv 推移.csv          # CSV 保存(UTF-8 変換、- で標準出力)
uv run mf-sbi asset-history --month 2026-06 --csv - # 指定月の日次 CSV
uv run mf-sbi categories                 # 家計簿カテゴリ一覧(ID 確認用)
uv run mf-sbi add --amount 500 --content コーヒー --large-id 11 --middle-id 43 --execute
uv run mf-sbi memo <transaction_id> "メモ" --execute   # 明細メモ更新
uv run mf-sbi delete <transaction_id> --execute        # 手入力明細の削除
uv run mf-sbi refresh                    # 一括更新の dry-run(既定)
uv run mf-sbi refresh --execute          # 一括更新を実行
uv run mf-sbi refresh --account-id <ID> --execute --wait   # 口座別更新+完了待ち
```

- 「月」はサービス側のユーザー設定の締め日起点の期間です(例: 25日始まりなら
  `--month 2026-05` は 05/25〜06/24)。
- `refresh` は金融機関への再集計を発生させるため dry-run が既定です。実行・dry-run とも
  `logs/audit-YYYY-MM.log` に監査記録が残ります。

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

## 制約

- 入出金明細の `/cf/csv` エクスポートはプレミアム限定のため使用せず、HTML を解析します
- 資産推移の CSV はプレミアム制限なし。サマリは日次直近約10日+月次約12ヶ月、
  `--month` 指定でデータ登録以降の任意の月の日次全日分が取得できます
