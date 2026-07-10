# 入出金明細(観測: 2026-07-10)

## エンドポイント

- `GET /cf`(HTML、セッションに保持された「表示中の期間」の明細を返す)
- 期間切替: `POST /cf/fetch`
  - data: `from=YYYY/M/D`(任意で `account_id_hash`、`service_id`)
  - ヘッダ: `X-CSRF-Token`(meta から)、`X-Requested-With: XMLHttpRequest`
  - レスポンスは text/javascript(画面書き換え用)。**中身は使わず**、直後に `GET /cf` して解析する
- 期間はユーザー設定の締め日起点(例: 25日始まり `2026/06/25 - 2026/07/24`)。
  ページ内の月選択リンク `a.js-uikit-year-month-select-dropdown-link` の `data-from` に
  各月の開始日(`YYYY/M/25` 等)が入っており、開始「日」はここから読める。

## 解析

- 表示期間ラベル: `.fc-header-title h2`(例 `2026/06/25 - 2026/07/24`)
- 明細テーブル: `#cf-detail-table tbody tr`(ページネーションなし、期間内全件)
  - `td.date`: `07/10(金)`(年はラベルの期間から補完)
  - `td.content`: 摘要
  - `td.amount`: 金額。`plus-color`=収入、`minus-color`=支出(負号付き)。
    振替行は色クラスなしで `-100,000 (振替)` の形式
  - 振替行は `tr.mf-grayout`(計算対象外)。保有金融機関セル(`td.calc`、クラス `note` なし)に
    出金元と入金先の2口座が入る
  - 通常行の保有金融機関: `td.note.calc`
  - `td.lctg` / `td.mctg`: 大項目 / 中項目(振替行は空)
  - `td.memo`: メモ
- 月次サマリ: `#monthly_total_table_kakeibo`(当月収入/当月支出/当月収支)

## 制約

- `/cf/csv` `/cf/excel.xls` はプレミアム限定(無課金では `302 /` で拒否)→ HTML 解析が一次手段
- `GET /cf?from=...&month=...&year=...` の GET パラメータは無視される(セッション基準)
