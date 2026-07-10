# 家計診断(観測: 2026-07-11)

## エンドポイント

- `GET /analysis/diagnoses/<年>/<月>`(HTML)
- `GET /analysis/diagnoses/latest` → 最新月へリダイレクト(最終 URL から年月が読める)

## 埋め込み JSON(一次データ源)

月次レポートと同形式で `<script>` に埋め込まれる(トップレベルキーは引用符なし):

```js
window.PFMApp.Analysis.Diagnoses = {
  ComparisonWithIdeal: {"balance_of_payment":{"actual":6241,"ideal":1123310},
                        "expense":{"actual":1117069,"ideal":0}},
  BudgetBalance: {"categories":[...上位5項目名...],
                  "ideal":{"data":[{"percentage":100,"amount":0},...]},
                  "actual":{"data":[...]}},
  CategoryComparison: {"categories":[{"id":14,"name":"衣服・美容","icon":"icon-fashion"},...],
                       "ideal":{"data":[...]}, "actual":{"data":[...]}},
  IsDiagnosisAvailable: false,
  IsFirstVisit: true,
  IsPremiumUser: false
};
```

- `CategoryComparison.categories[i]` と `ideal.data[i]` / `actual.data[i]` は同順で対応する
- **属性情報(生年・家族構成など)未設定でも JSON は埋め込まれる**が、
  `IsDiagnosisAvailable: false` で ideal 側は全て 0(百分率も比較不能値)
- 属性設定後の ideal 値の実データは未観測(要注意)

## 失敗の見分け方

- 未認証: `302 /users/sign_in`
- `PFMApp.Analysis.Diagnoses` 欠落: 仕様変更の可能性
