# 家計簿 Excel / CSV 出力(観測: 2026-07-11)

## 結論: 無課金では取得不可(実装なし)

- `GET /cf/excel.xls`、`GET /cf/excel`、`GET /cf/csv` はいずれも無課金アカウントでは
  **トップページ(`/`)へリダイレクト**され、ファイルは返らない(HTTP 200 / text/html)
- プレミアム会員限定機能。リダイレクト先 HTML にプレミアム誘導が含まれる

## 判定方法

- 未認証と同様に content-type が `text/html` になることで判別できる
  (取得できる場合は CSV/Excel の content-type・バイナリになるはず。未観測)

## 代替手段

- 明細データ: `GET /cf` の HTML 解析(実装済み: `list_transactions`)
- 資産推移 CSV: `GET /bs/history/csv` はプレミアム制限なし(docs/specs/assets/history.md)

プレミアム契約時に再観測すること。
