# 支出内訳(収支内訳)(観測: 2026-07-11)

## エンドポイント

- `GET /cf/summary`(HTML)。**支出内訳のみ**(ページ h1 は「支出」。収入内訳の表はない)
- 期間指定: `GET /cf/summary?from=YYYY/MM/DD`
  - `from` は**対象期間内の任意の日付**(締め日起点。開始日は `/cf` の月選択リンク
    `data-from` から読める。docs/specs/cf/transactions.md の `_read_start_day` 参照)
  - 前月/翌月ナビの `a[href*="from="]` からも遷移先の from が取れる

## 構造

- 期間ラベル: `.from-to`(例 `2026/06/25 - 2026/07/24`)
- 内訳テーブル: `#table-outgo`(`table table-bordered`)。同一データの `table.table-out`(id なし)も
  あるが、id のある `#table-outgo` を使う
- ヘッダ行: `項目 | 金額 | 割合`
- データ行:
  - **大項目合計行**: `tr.sum`。項目名は `食費 合計` のように「◯◯ 合計」
  - **中項目行**: クラスなし。直前の大項目合計に属する(食料品・外食 など)
  - いずれも金額(`td` テキスト、`1,234円` 形式)と割合(`12.3%` 形式)を持つ
  - `td.number` クラスが付く場合あり(位置ではなくヘッダ順で 金額=2列目・割合=3列目)
- 当月合計: `#monthly_total_table`(当月収入 / 当月支出 / 当月収支。/cf と同じ)

## 既存機能との違い

- `monthly`(/cf/monthly): 月をまたぐ横断表(割合なし)
- `report`(/analysis/monthly_reports): 分析の埋め込み JSON(前月・前年比つき、月次固定)
- 本機能: **1期間の支出をカテゴリ別に金額+割合で返す**(期間は `?from=` で任意指定)

## 失敗の見分け方

- 未認証: `302 /users/sign_in`
- `#table-outgo` 欠落: 仕様変更の可能性
