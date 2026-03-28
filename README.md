# せらボット

[cabinattendant.blog](https://cabinattendant.blog/) をもとにした個人チャットボットです。
元CA・投資家の「せら」のペルソナで、ブログの内容（航空・高配当株投資・FIRE）について話せます。

## セットアップ

```bash
# 依存関係インストール
pip install -r requirements.txt

# APIキーを設定
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定
```

## 使い方

```bash
# ブログ記事を取得してチャット開始
python main.py --update

# チャットのみ（既存のナレッジベースを使用）
python main.py

# 記事更新のみ（チャットなし）
python main.py --update-only
```

チャット中のコマンド:
- `reset` - 会話履歴をリセット
- `reload` - ナレッジベースを再読み込み
- `exit` - 終了

## 自動更新（GitHub Actions）

`.github/workflows/update.yml` により、1日4回（6時/12時/18時/0時 JST）自動的にブログを巡回し、新着記事があれば `data/knowledge_base.json` を更新してコミットします。

手動実行は GitHub の Actions タブから `workflow_dispatch` で行えます。

## 構成

```
sera-bot/
├── main.py                    # エントリーポイント（CLI）
├── bot.py                     # Claude API チャットボット
├── scraper.py                 # ブログスクレイパー
├── data/
│   └── knowledge_base.json    # 記事データ（自動更新）
├── .github/
│   └── workflows/
│       └── update.yml         # 自動更新ワークフロー
├── requirements.txt
└── .env.example
```
