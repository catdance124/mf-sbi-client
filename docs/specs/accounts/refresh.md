# 連携口座の更新実行(観測: 2026-07-10、追検証: 2026-07-11)

## エンドポイント

- 一括更新: `POST /faggregation_queue2`
  - `/accounts` ほかに `<a href="/faggregation_queue2" data-method="post">一括更新</a>`(Rails UJS)
  - **無料プランでは受理(accepted)されるだけで実処理されない**(下記「プラン差」)
- 口座別更新: `POST /faggregation_queue2/<account_id_hash>`
  - `/accounts` の行内フォーム(hidden `authenticity_token` + `commit=更新`)
  - **無料プランでも実際に集計が走る**(実測で反映を確認)

## プラン差(実測: 2026-07-11、無料プラン `dimension3=free`)

- 一括更新 `POST /faggregation_queue2`(id なし)を実行 → 15 分間、全口座の最終取得時刻が
  朝の定時更新(06:00)から進まず、状態も「更新中」のまま固定。**実処理されていない**。
  一括更新は UI 上プレミアム機能で、サーバーは 200 で受理するが無料では集計を行わない建て付け。
- 口座別更新 `POST /faggregation_queue2/<id>`(ある連携口座)→ 十数秒後に最終取得時刻が
  実行時刻へ更新。**無料プランで有効**。
- 実装方針: 全口座更新は「口座別更新のループ」で行う(id なし一括には依存しない)。
  `refresh_all_accounts` = `refresh_account` を全連携口座に対して順次実行。

## 認証・トークン

- `meta[name="csrf-token"]` を `X-CSRF-Token` ヘッダで送る(UJS 相当)

## 更新の完了検知

- 集計は非同期。`GET /accounts` の「更新状態」列をポーリングし、
  「更新中」系の表示が消えたら完了とみなす(interval/timeout は引数で調整)。

## 注意

- 破壊的相当の操作(金融機関への集計アクセスを発生させる)。dry-run 既定 + 監査ログ必須。
