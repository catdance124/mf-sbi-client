# 口座別詳細(観測: 2026-07-11)

## エンドポイント

- `GET /accounts/show/<account_id_hash>`(HTML)
- account_id_hash は口座一覧(`/accounts`)の各フォームから取得できるものと同一

## 構造

- `section.accounts-form`:
  - `h1.show-title`: 金融機関名
  - `h1.heading-small`: `ラベル：値` 形式のサマリ行。内容は口座種別で異なる:
    - 銀行: `資産総額：123,456円`
    - カード: `負債総額：-12,345円`、`引き落とし予定額：未定`
    - 入れ子セクションの `合計：…` も heading-small で拾われるため除外すること
  - 最初の `table.table-bordered`: サブ口座一覧。ヘッダは種別で異なる
    (銀行: `名称 | 種類 | 番号 | 残高`、カード: `名称 | 種類 | 番号 | 引き落とし予定額`)。
    **カードでは行頭に余分な空セルが入る**(ヘッダ数+1 セル)ので右詰めで対応付ける
- `section.bs-detail`(複数): 資産クラス別内訳(id 例 `portfolio_det_depo`)
  - `h1`: 資産クラス名(`預金・現金`、`負債` など)
  - 内部の table: ヘッダは種別で異なる(`種類・名称 | 残高` / `名称 | 残高 | 取得日` など)
- `section#in_out`: 当該口座の入出金明細
  - 期間ラベル: `.fc-header-title h2`(例 `2026/06/25 - 2026/07/24`)
  - `#cf-detail-table`: /cf と同一構造(td.date / td.content / td.amount / td.note.calc /
    td.lctg / td.mctg。docs/specs/cf/transactions.md 参照)
  - 期間切替 UI もあるが未実装(表示中期間のみ取得)

## 失敗の見分け方

- 未認証: `302 /users/sign_in`
- `section.accounts-form` 欠落: 仕様変更または不正な account_id_hash の可能性
