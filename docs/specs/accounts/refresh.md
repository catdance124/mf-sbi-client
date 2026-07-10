# 連携口座の更新実行(観測: 2026-07-10)

## エンドポイント

- 一括更新: `POST /faggregation_queue2`
  - `/accounts` ほかに `<a href="/faggregation_queue2" data-method="post">一括更新</a>`(Rails UJS)
- 口座別更新: `POST /faggregation_queue2/<account_id_hash>`
  - `/accounts` の行内フォーム(hidden `authenticity_token` + `commit=更新`)

## 認証・トークン

- `meta[name="csrf-token"]` を `X-CSRF-Token` ヘッダで送る(UJS 相当)

## 更新の完了検知

- 集計は非同期。`GET /accounts` の「更新状態」列をポーリングし、
  「更新中」系の表示が消えたら完了とみなす(interval/timeout は引数で調整)。

## 注意

- 破壊的相当の操作(金融機関への集計アクセスを発生させる)。dry-run 既定 + 監査ログ必須。
