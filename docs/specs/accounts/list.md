# 口座一覧・残高(観測: 2026-07-10)

## エンドポイント

- `GET /accounts`(HTML)

## 構造

- `table.table-striped`、thead ヘッダ:
  `金融機関 | 資産 | 登録日（最終取得日） | 更新状態 | 更新 | 編集 | 削除`
- 列はヘッダ文言で特定する(位置依存禁止)
- account_id_hash は行内の各フォームから取得できる:
  - 更新: `form[action^="/faggregation_queue2/"]` → `/faggregation_queue2/<account_id_hash>`
  - 編集: `form[action^="/accounts/edit/"]`
  - 削除フォームの hidden `account_id_hash`
- 手元の現金など手動口座には更新フォームがない(更新非対象)

## 失敗の見分け方

- 未認証: `302 /users/sign_in`
- テーブル欠落: 仕様変更の可能性
