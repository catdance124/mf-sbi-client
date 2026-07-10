# Changelog

## 未リリース

- `asset-history --month YYYY-MM`: 指定月の日次資産推移(全日分)を CSV エンドポイントから取得
- `asset-history --csv PATH`: サービスの CSV(cp932)を UTF-8 に変換して保存(`-` で標準出力)
- ライブラリ API 追加: `get_monthly_asset_history()` / `get_asset_history_csv()` /
  `get_monthly_asset_history_csv()`

## v0.1.0 (2026-07-10)

初回リリース。

- ログイン(メールアドレス+パスワード)とセッション Cookie キャッシュ、認証切れ時の自動再ログイン
- `accounts`: 連携口座の一覧・残高・更新状態
- `transactions`: 入出金明細(締め日起点の月単位、複数月イテレーション対応)
- `assets` / `asset-history`: 資産内訳・資産推移(日次+月次)
- `refresh`: 連携口座の更新実行(一括/口座別、dry-run 既定、監査ログ、完了待ちポーリング)
