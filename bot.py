"""
Sera bot - A personal chatbot based on cabinattendant.blog
Uses the Claude API with a knowledge base built from the blog's articles.
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

KB_PATH = Path(__file__).parent / "data" / "knowledge_base.json"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """あなたは「せら」です。
もとはCAとして働いていましたが、年収400万円という現実に向き合い、高配当株投資と長期積立投資でFIRE（経済的自立・早期退職）を目指している女性です。

【キャラクター設定】
- 元CA（キャビンアテンダント）で、航空・旅行業界の知識が豊富
- 高配当株・成長株・NISA・投資信託などの個人投資に詳しい
- FIREを本気で目指しており、お金に対してシビアかつ前向き
- 口調は親しみやすく、難しい話もわかりやすく噛み砕いて説明する
- 自分の経験談（CA時代のエピソードや投資体験）を交えながら話す
- 必要以上に謙遜せず、自分の意見をはっきり伝える

【回答スタイル】
- 口語的・フレンドリーな日本語で話す
- 専門用語は使うが、必ず説明を添える
- 自分のブログ記事の内容を根拠として使う
- 長すぎず、要点を押さえた回答をする
- 投資は自己責任であることを忘れず、あくまで「私の考え」として伝える

以下のブログ記事の知識をもとに回答してください。知識にない内容を聞かれたときは「まだブログには書いていないんだけど…」と前置きして一般的な知識で答えてOK。"""


def load_knowledge_base() -> dict:
    if KB_PATH.exists():
        with open(KB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "articles": []}


def build_knowledge_context(kb: dict, max_chars: int = 20000) -> str:
    """Build a context string from the knowledge base for the system prompt."""
    articles = kb.get("articles", [])
    if not articles:
        return "（まだ記事データがありません。scraper.py を実行してください）"

    lines = ["【せらのブログ記事一覧】\n"]
    total = 0
    for art in reversed(articles):  # newest first
        entry = (
            f"## {art.get('title', '(タイトルなし)')}\n"
            f"URL: {art.get('url', '')}\n"
            f"公開日: {art.get('published_at', '')[:10]}\n"
            f"{art.get('content', art.get('excerpt', ''))}\n\n"
        )
        if total + len(entry) > max_chars:
            break
        lines.append(entry)
        total += len(entry)

    updated = kb.get("last_updated", "不明")
    lines.append(f"\n（最終更新: {updated}）")
    return "".join(lines)


class SeraBot:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY が設定されていません。"
                ".env ファイルを作成するか、環境変数に設定してください。"
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.history: list[dict] = []
        self._reload_kb()

    def _reload_kb(self):
        kb = load_knowledge_base()
        knowledge = build_knowledge_context(kb)
        self.system = f"{SYSTEM_PROMPT}\n\n{knowledge}"
        updated = kb.get("last_updated") or "未取得"
        article_count = len(kb.get("articles", []))
        print(f"[bot] ナレッジベース読み込み完了 (記事数: {article_count}, 最終更新: {updated[:10] if updated != '未取得' else updated})")

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=self.system,
            messages=self.history,
        )
        assistant_message = response.content[0].text
        self.history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def reset(self):
        self.history = []

    def reload(self):
        """Reload the knowledge base (after running scraper)."""
        self._reload_kb()
        self.reset()
