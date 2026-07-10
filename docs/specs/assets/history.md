# 資産推移(観測: 2026-07-10)

## エンドポイント

- `GET /bs/history`(HTML)

## 構造

- `table.table-bordered` 1つに日次(直近約10日)と月次(過去約12ヶ月の月末)が混在:
  - thead: `日付 | 合計 | <資産クラス列...> | 詳細`(資産クラス列はユーザーの保有内容に依存)
  - tbody 行: `th`=日付(`2026-07-10`)、`td.total`=合計、以降は資産クラスごとの金額
  - 詳細リンク: 日次 `/bs/history/list/<YYYY-MM-DD>`、月次 `/bs/history/list/<YYYY-MM-DD>/monthly`
    (月次判定はこのリンク形式で行える)

## 制約

- `/bs/history/csv` `/bs/history/excel` はプレミアム限定
- グラフ描画用の追加 XHR はなし(サーバレンダリング)
