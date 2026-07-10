# 月次レポート(観測: 2026-07-11)

## エンドポイント

- `GET /analysis/monthly_reports/<年>/<月>`(HTML)
- `GET /analysis/monthly_reports/latest` → 最新月へリダイレクト(最終 URL から年月が読める)
- 2024/1 までのアーカイブ月リンクあり(それ以前は未観測)

## 埋め込み JSON(一次データ源)

ページ内 `<script>` に以下の形で埋め込まれる。トップレベルのキーは**引用符なし**(JS リテラル)、
値は JSON として妥当:

```js
window.PFMApp.Analysis.Reports = {
  incomeSummary: {...},
  incomeMiddleCatData: {...},
  outgoSummary: {...},
  outgoLargeCategoryData: {...},
  outgoMiddleCategoryData: {...},
  outgoDetailData: {...}
};
```

- サマリノード共通形: `{"s": 金額(float), "c": {<key>: 子ノード}, "name": 名称,
  "s_compared_prev": 前月差, "s_compared_prev_year": 前年同月差}`
  - `incomeSummary.c` / `outgoSummary.c`: 大項目(食費・通信費など)。キーは large_cat_key
  - 大項目の `c`: 中項目(食料品・外食など)。キーは中項目 ID
  - 支出大項目には `s_compared_spending_target`(予算比)が付くことがある
- **画面上の「収入内訳」「支出内訳」「資産推移」はプレミアム会員限定表示だが、
  この JSON は無課金でも埋め込まれている**(資産推移の種類別データは JSON にも含まれない)

## HTML(補助データ)

- 総資産: `.monthly-report-sum-head-block` 内
  - `.amount`: `￥719,041`、`.ratio`: `+147.64%&nbsp;(前月比)`
- 収支: `.monthly-report-sum-balance` のテキスト
  `収入 ￥806,104 - 支出 ￥735,000 = 収支 ￥71,104`
  (各項目は `.monthly-report-sum-balance-item` 単位)

## 失敗の見分け方

- 未認証: `302 /users/sign_in`
- `PFMApp.Analysis.Reports` 欠落: 仕様変更の可能性
- データのない過去月: 未観測(要注意)
