# Changelog

## v0.3.0 (2026-07-11)

### 追加

- `asset detail`: 資産クラス別の保有明細(銘柄ごとの評価損益など)を表示
- ライブラリ API 追加: `get_portfolio_details()` — `/bs/portfolio` の明細テーブルを
  セクション要素 id(`portfolio_det_eq` など)ごとに {ヘッダ文言: セル原文} の行リストで返す
  (内部 API が存在しないことを観測済みのため HTML 解析。docs/specs/assets/portfolio.md 参照)

## v0.2.0 (2026-07-11)

### 破壊的変更

- CLI をドメイン別2階層(`auth` / `account` / `cf` / `asset` / `analysis`)に再設計。
  旧コマンド名は使用不可: `accounts`→`account list`、`account`→`account show`、
  `refresh`→`account refresh`、`assets`→`asset list`、`asset-history`→`asset history`、
  その他(`transactions` など)は `cf` / `analysis` グループ配下へ移動
- 書き込み系(`cf add` / `cf memo` / `cf delete` / `account refresh`)の `--execute` を廃止し、
  既定で実行 + `--dry-run` で内容確認のみに反転。ルートの `--dry-run` フラグは各コマンドへ移動
  (ライブラリ API の `dry_run=True` 既定と監査ログは従来どおり)

### 追加

- `cf monthly`: 月次収支リスト取得(/cf/monthly)
- `cf summary`: 支出内訳取得(/cf/summary)
- `cf add` / `cf memo` / `cf delete`: 家計簿の手入力・メモ編集・削除
  (/cf/create、/cf/update、DELETE /cf/`<id>`)
- `cf categories`: 家計簿カテゴリ一覧
- `account show`: 口座別詳細取得(/accounts/show)
- `analysis report`: 月次レポート取得(/analysis/monthly_reports)
- `analysis diagnosis`: 家計診断取得(/analysis/diagnoses)
- `asset history --month YYYY-MM`: 指定月の日次資産推移(全日分)を CSV エンドポイントから取得
- `asset history --csv PATH`: サービスの CSV(cp932)を UTF-8 に変換して保存(`-` で標準出力)
- ライブラリ API 追加: `get_monthly_asset_history()` / `get_asset_history_csv()` /
  `get_monthly_asset_history_csv()` ほか各操作に対応するメソッド

### 変更

- `account refresh`: 一括更新エンドポイントが無料プランで実処理されないため、
  全連携口座を口座別更新でループする方式に変更

## v0.1.0 (2026-07-10)

初回リリース。

- ログイン(メールアドレス+パスワード)とセッション Cookie キャッシュ、認証切れ時の自動再ログイン
- `accounts`: 連携口座の一覧・残高・更新状態
- `transactions`: 入出金明細(締め日起点の月単位、複数月イテレーション対応)
- `assets` / `asset-history`: 資産内訳・資産推移(日次+月次)
- `refresh`: 連携口座の更新実行(一括/口座別、dry-run 既定、監査ログ、完了待ちポーリング)
