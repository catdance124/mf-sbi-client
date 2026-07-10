# 家計簿の手入力(観測: 2026-07-11)

## エンドポイント

- `POST /cf/create`(通常のフォーム POST、成功時 200 で /cf に戻る)

## リクエスト

`/cf` ページの `form[action="/cf/create"]` を再現する:

- `authenticity_token`: 同フォームの hidden から取得(meta の CSRF トークンではなくフォーム側)
- `user_asset_act[is_transfer]`: `0`
- `user_asset_act[is_income]`: 収入 `1` / 支出 `0`
- `user_asset_act[payment]`: `2`(観測時のラジオ値。UI のタブ切替は is_income 側で表現される)
- `user_asset_act[updated_at]`: `YYYY/MM/DD`(datepicker の format `yyyy/mm/dd`)
- `user_asset_act[recurring_flag]`: `0`(繰り返し入力は未対応)
- `user_asset_act[amount]`: 正の整数(支出でも正。符号は is_income で決まる)
- `user_asset_act[sub_account_id_hash]`: `0` = 口座なし(「なし」表示)
- `user_asset_act[large_category_id]` / `user_asset_act[middle_category_id]`: `0` = 未分類
- `user_asset_act[content]`: 内容(50 文字まで)
- `commit`: `保存する`

## カテゴリ ID の取得

- `/cf` ページの `ul.main_menu.plus`(収入)/ `ul.main_menu.minus`(支出)
- 大項目: `a.l_c_name`(`id` 属性が large_category_id)
- 中項目: 大項目の `li.dropdown-submenu` 内の `a.m_c_name`(`id` 属性が middle_category_id)

## 検証(2026-07-11 実施)

- 未分類・1円・支出で作成 → `#cf-detail-table` に行が出現、行 id `js-transaction-<数値id>`
- 手入力行は `td.delete` に削除リンクが付く(自動取得行は削除不可)

## 安全性

- 書き込み操作のため dry-run 既定 + 監査ログ必須
