"""
Blog scraper for cabinattendant.blog
Fetches articles and stores them in data/knowledge_base.json
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BLOG_URL = os.getenv("BLOG_URL", "https://cabinattendant.blog/")
KB_PATH = Path(__file__).parent / "data" / "knowledge_base.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def load_knowledge_base() -> dict:
    if KB_PATH.exists():
        with open(KB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "articles": []}


def save_knowledge_base(kb: dict) -> None:
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)


def fetch_page(url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.RequestException as e:
            print(f"[scraper] fetch failed ({url}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def try_wp_rest_api() -> list[dict]:
    """Try to fetch articles via WordPress REST API (fastest method)."""
    api_url = urljoin(BLOG_URL, "wp-json/wp/v2/posts")
    params = {
        "per_page": 50,
        "_fields": "id,title,link,content,excerpt,date,slug",
    }
    try:
        resp = requests.get(api_url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code != 200:
            return []
        posts = resp.json()
        articles = []
        for p in posts:
            content_html = p.get("content", {}).get("rendered", "")
            excerpt_html = p.get("excerpt", {}).get("rendered", "")
            title = BeautifulSoup(p.get("title", {}).get("rendered", ""), "lxml").get_text()
            content = BeautifulSoup(content_html, "lxml").get_text(separator="\n").strip()
            excerpt = BeautifulSoup(excerpt_html, "lxml").get_text().strip()
            articles.append({
                "id": str(p["id"]),
                "url": p.get("link", ""),
                "title": title,
                "excerpt": excerpt,
                "content": content[:3000],
                "published_at": p.get("date", ""),
            })
        print(f"[scraper] WP REST API: found {len(articles)} articles")
        return articles
    except Exception as e:
        print(f"[scraper] WP REST API failed: {e}")
        return []


def parse_article_page(url: str) -> str:
    """Fetch and extract full article text from a single article URL."""
    html = fetch_page(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    # Try common WordPress article selectors
    for selector in [
        "article .entry-content",
        "article .post-content",
        ".entry-content",
        ".post-content",
        "article",
        ".content",
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator="\n").strip()[:3000]
    return ""


def scrape_index_page() -> list[dict]:
    """Scrape the blog index page to find article links."""
    html = fetch_page(BLOG_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    seen_urls = set()
    articles = []

    # Collect all article links on index page
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Resolve relative URLs
        full_url = urljoin(BLOG_URL, href)
        parsed = urlparse(full_url)
        # Only follow same-domain, path-only URLs (article slugs)
        if parsed.netloc != urlparse(BLOG_URL).netloc:
            continue
        path = parsed.path.strip("/")
        if not path or path in ("", "category", "tag", "author", "page"):
            continue
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Try to extract title from link text or surrounding heading
        title = a_tag.get_text(strip=True)
        if len(title) < 5:
            # Try parent heading
            parent = a_tag.find_parent(["h1", "h2", "h3"])
            if parent:
                title = parent.get_text(strip=True)

        if len(title) < 5:
            continue

        articles.append({
            "id": path,
            "url": full_url,
            "title": title,
        })

    print(f"[scraper] Index page: found {len(articles)} candidate links")
    return articles


def fetch_articles_with_content(article_stubs: list[dict], existing_urls: set) -> list[dict]:
    """For each stub not already in KB, fetch the full article content."""
    new_articles = []
    for stub in article_stubs:
        if stub["url"] in existing_urls:
            continue
        print(f"[scraper] Fetching: {stub['url']}")
        content = parse_article_page(stub["url"])
        stub["content"] = content
        stub["excerpt"] = content[:200].replace("\n", " ")
        stub["published_at"] = datetime.now(timezone.utc).isoformat()
        new_articles.append(stub)
        time.sleep(1)  # polite delay
    return new_articles


def run_update() -> int:
    """Main update function. Returns number of new articles added."""
    print("[scraper] Starting update...")
    kb = load_knowledge_base()
    existing_urls = {a["url"] for a in kb["articles"]}

    # 1. Try WordPress REST API (cleanest)
    new_articles = try_wp_rest_api()
    if new_articles:
        added = [a for a in new_articles if a["url"] not in existing_urls]
    else:
        # 2. Fallback: scrape index + fetch each article
        stubs = scrape_index_page()
        added = fetch_articles_with_content(stubs, existing_urls)

    if added:
        kb["articles"].extend(added)
        # Keep latest 200 articles
        kb["articles"] = kb["articles"][-200:]
        kb["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_knowledge_base(kb)
        print(f"[scraper] Added {len(added)} new articles. Total: {len(kb['articles'])}")
    else:
        print("[scraper] No new articles found.")
        kb["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_knowledge_base(kb)

    return len(added)


if __name__ == "__main__":
    run_update()
