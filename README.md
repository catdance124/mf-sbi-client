# mf-sbi-client

マネーフォワード for 住信SBIネット銀行(https://ssnb.x.moneyforward.com/)の非公式クライアントライブラリ + CLI。

自分のアカウントのデータ(入出金明細・口座残高・資産推移)を取得し、連携口座の更新を実行できます。

## セットアップ

```sh
uv sync
cp .env.example .env   # MF_SBI_EMAIL / MF_SBI_PASSWORD を記入
```

## 使い方

```sh
uv run mf-sbi login-check
```

(コマンドは実装中。詳細は追って追記)

## セッションキャッシュ

ログイン後の Cookie は `.session/cookies.json`(パーミッション 600)に保存され、
有効な間は再ログインしません。
