# ログイン(観測: 2026-07-10)

## フロー

1. `GET /users/sign_in`
   - 同一ドメイン内のフォーム(外部 SSO へのリダイレクトなし)
   - `form[action$="/session"]` の hidden `authenticity_token` を取得
   - reCAPTCHA なし
2. `POST /session`(`Referer: /users/sign_in` 付与)
   - `authenticity_token`
   - `sign_in_session_service[email]`
   - `sign_in_session_service[password]`
   - `commit=ログイン`
3. 成功時は `/users/two_step_verifications/new`(2段階認証の**設定勧誘ページ**)へ 302 する
   ことがあるが、この時点でセッションは確立済み。ページ遷移は不要で無視してよい。

## セッション

- Cookie: `_moneybook_session`(セッション本体)、`identification_code`
- 未認証で保護ページ(`/accounts` `/cf` `/bs/*`)に GET → `302 /users/sign_in`
- 認証チェック: `GET /accounts`(リダイレクト追従なし)が 200 なら認証済み

## 失敗の見分け方

- 認証失敗: POST 後も `/users/sign_in` に留まる(エラーメッセージ表示)
- CSRF トークン欠落: 422

## CSRF

- 各ページの `meta[name="csrf-token"]` を Ajax POST の `X-CSRF-Token` ヘッダに使う
