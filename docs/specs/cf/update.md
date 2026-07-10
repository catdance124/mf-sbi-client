# 家計簿明細の編集・削除(観測: 2026-07-11)

## 編集(メモ更新)

- `PUT /cf/update`(実体は rails の `_method=put` を伴う POST でも通る)
- 各明細行(`tr#js-transaction-<id>`)内の `form[action="/cf/update"]` を再現する:
  - フォームは data-remote 相当で **authenticity_token を持たない**。
    CSRF は meta トークンを `X-CSRF-Token` ヘッダで送る(`X-Requested-With: XMLHttpRequest`)
  - hidden をそのまま送り直す: `user_asset_act[id]`、`original_amount`、
    `user_asset_act[sub_account_id_hash]`、`user_asset_act[table_name]`、
    `user_asset_act[is_income]` など
  - **画面の JS はメモ変更時に `user_asset_act[is_target]` /
    `user_asset_act[large_category_id]` / `user_asset_act[middle_category_id]` を
    空文字にして送る**(空 = 変更なし)。空にしないと HTTP 500 になる
  - `user_asset_act[memo]`: 新しいメモ(20 文字まで)
- 成功時 200(text/javascript)

## 削除(手入力行のみ)

- 手入力行の `td.delete a[data-method=delete]` の href:
  `/cf/<id>?from=YYYY/MM/DD&sorted=date&table_name=user_asset_act`
- `_method=delete` + `authenticity_token`(meta トークン)の POST で削除できる。成功時 200
- 自動取得行には削除リンクがない(`td.delete` に title のみ)

## 対象行の特定

- 行 id: `js-transaction-<id>`。`<id>` は編集フォーム hidden `user_asset_act[id]` と同値
- 対象行が表示中の期間にない場合は先に `POST /cf/fetch` で期間を切り替える

## 検証(2026-07-11 実施)

- テスト行(手入力・1円)に対しメモ更新 → 反映確認 → 削除 → 行消滅を確認

## 安全性

- 書き込み操作のため dry-run 既定 + 監査ログ必須
