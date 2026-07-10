# 資産推移(観測: 2026-07-10)

## エンドポイント

- `GET /bs/history`(HTML)

## 構造

- `table.table-bordered` 1つに日次(直近約10日)と月次(過去約12ヶ月の月末)が混在:
  - thead: `日付 | 合計 | <資産クラス列...> | 詳細`(資産クラス列はユーザーの保有内容に依存)
  - tbody 行: `th`=日付(`2026-07-10`)、`td.total`=合計、以降は資産クラスごとの金額
  - 詳細リンク: 日次 `/bs/history/list/<YYYY-MM-DD>`、月次 `/bs/history/list/<YYYY-MM-DD>/monthly`
    (月次判定はこのリンク形式で行える)

## CSV(観測: 2026-07-10 追記)

- `GET /bs/history/csv`: サマリ(日次 直近約10日 + 月次 約12ヶ月)の CSV。**プレミアム制限なし**
  (cf の `/cf/csv` と異なり無課金でも取得できる)
- `GET /bs/history/list/<YYYY-MM-DD>/monthly/csv`: `<YYYY-MM-DD>` はその月の月末日。
  **その月の日次全日分**の CSV。リンク表示のない古い月も指定可(データ登録前の月はヘッダのみ)
- ヘッダ例: `"日付","合計（円）","預金・現金（円）","ポイント（円）"`、値は数値のみ(カンマ・円なし)
- **文字コードは cp932**(content-type は `text/csv; charset=utf-8` と偽るので注意)
- 未認証・拒否時は HTML が返る(content-type で判定)

## 月次詳細ページ(HTML)

- `GET /bs/history/list/<月末日>/monthly`: その月の日次テーブル(CSV と同内容 + 詳細リンク)

## 制約

- グラフ描画用の追加 XHR はなし(サーバレンダリング)
