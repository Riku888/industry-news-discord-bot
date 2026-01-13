import os
import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any

import feedparser
import requests
import yaml
from dateutil import parser as dateparser

# ★ 追加：DB / Analytics / Dashboard
from src.db import get_conn, init_db, upsert_articles
from src.analytics import (
    query_daily_counts,
    write_daily_counts,
    compute_keywords,
    write_keywords,
)
from src.dashboard import write_dashboard_html


# ----------------------------
# Utility
# ----------------------------
def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def parse_date(entry: dict) -> str:
    raw = entry.get("published") or entry.get("updated") or ""
    if not raw:
        return ""
    try:
        dt = dateparser.parse(raw)
        if not dt:
            return ""
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


def tag_category(title: str, keywords: Dict[str, List[str]]) -> str:
    t = title.lower()
    for cat, words in keywords.items():
        for w in words:
            if w.lower() in t:
                return cat
    return "その他"


def make_id_from_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


# ----------------------------
# Industry relevance filter
# ----------------------------
def is_relevant_to_industry(
    item: Dict[str, str],
    industry_keywords: List[str]
) -> bool:
    text = (item["title"] + " " + item["url"]).lower()
    return any(k.lower() in text for k in industry_keywords)


# ----------------------------
# Fetch (RSS)
# ----------------------------
def fetch_rss_items(
    sources: List[Dict[str, str]],
    keywords: Dict[str, List[str]],
    per_source_limit: int = 30
) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for src in sources:
        name = src["name"]
        rss_url = src["rss"]

        feed = feedparser.parse(rss_url)

        for e in feed.entries[:per_source_limit]:
            title = normalize_whitespace(e.get("title", ""))
            link = (e.get("link") or "").strip()
            if not title or not link:
                continue

            date = parse_date(e)
            category = tag_category(title, keywords)

            items.append({
                "date": date,
                "source": name,
                "title": title,
                "url": link,
                "category": category,
            })
    return items


def dedupe_by_url(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    out = []
    for it in items:
        url = it["url"]
        if url in seen:
            continue
        seen.add(url)
        out.append(it)
    return out


def pick_top(items: List[Dict[str, str]], n: int) -> List[Dict[str, str]]:
    def score(it):
        return (1 if it["date"] else 0, it["date"])
    return sorted(items, key=score, reverse=True)[:n]


# ----------------------------
# Discord (SAFE)
# ----------------------------
DISCORD_LIMIT = 2000


def split_discord_message(text: str, limit: int = DISCORD_LIMIT) -> List[str]:
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at].strip())
        text = text[split_at:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def post_to_discord_safe(webhook_url: str, content: str) -> None:
    messages = split_discord_message(content)
    for msg in messages:
        r = requests.post(webhook_url, json={"content": msg}, timeout=30)
        if r.status_code >= 300:
            raise RuntimeError(
                f"Discord webhook failed: {r.status_code} {r.text}"
            )


# ----------------------------
# OpenAI (Japanese brief)
# ----------------------------
def build_ai_input(items: List[Dict[str, str]]) -> str:
    lines = []
    for i, it in enumerate(items, start=1):
        lines.append(
            f"{i}. {it['title']} | 出典:{it['source']} | 日付:{it.get('date','')} | カテゴリ:{it.get('category','')} | {it['url']}"
        )
    return "\n".join(lines)


def summarize_with_openai_jp(industry: str, items: List[Dict[str, str]]) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing env var: OPENAI_API_KEY")

    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    input_text = build_ai_input(items[:10])

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
あなたは**「{industry} 専門メディア」の編集者**です。

【厳守ルール】
- {industry} と直接関係しない話題は**絶対に含めない**
- 地政学・金融・政治は「業界と直接関係する場合のみ」言及可
- 見出しに含まれていても、内容が業界外なら除外
- 推測で話題を広げない
- 事実を捏造しない

- 日本語で出力
- 全体は1200〜1800文字以内

出力フォーマット（必ずこの順）：
1) タイトル：{industry} デイリーブリーフ（{today}）
2) 今日の要点（3つ）
3) 今日の注目テーマ（短い一言）
4) 注目ニュースTop5：
   - 見出し / 出典 / なぜ重要か（1行） / URL
"""

    data = {
        "model": model,
        "input": [
            {"role": "system", "content": "You are a careful analyst. Do not invent facts."},
            {"role": "user", "content": prompt + "\n\n【素材】\n" + input_text},
        ],
    }

    resp = requests.post(url, headers=headers, json=data, timeout=60)
    if resp.status_code >= 300:
        raise RuntimeError(f"OpenAI API failed: {resp.status_code} {resp.text}")

    j = resp.json()
    return j["output"][0]["content"][0]["text"].strip()


# ----------------------------
# Message builder (No AI fallback)
# ----------------------------
def build_basic_message(industry: str, top_items: List[Dict[str, str]], total_items: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"📌 **{industry} ニュース速報**（{today}）")
    lines.append(f"取得件数：{total_items}（AI要約なし）")
    lines.append("")
    for i, it in enumerate(top_items, start=1):
        lines.append(f"{i}. {it['title']}")
        meta = f"出典:{it['source']}"
        if it["date"]:
            meta += f" / 日付:{it['date']}"
        meta += f" / カテゴリ:{it['category']}"
        lines.append(meta)
        lines.append(it["url"])
        lines.append("")
    return "\n".join(lines).strip()


# ----------------------------
# Main
# ----------------------------
def main():
    config = load_config("src/config.yaml")

    industry = config.get("industry", "業界")
    use_ai = bool(config.get("use_ai_summary", False))
    top_n = int(config.get("top_n", 5))

    keywords = config.get("keywords", {})
    sources = config.get("sources", [])

    if not sources:
        raise RuntimeError("No sources found in src/config.yaml")

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("Missing env var: DISCORD_WEBHOOK_URL")

    # 業界キーワードをフラット化
    industry_keywords: List[str] = []
    for words in keywords.values():
        industry_keywords.extend(words)

    # 1) fetch
    items = fetch_rss_items(sources, keywords, per_source_limit=30)

    # 2) normalize/dedupe
    items = dedupe_by_url(items)

    # 3) 業界フィルタ
    items = [it for it in items if is_relevant_to_industry(it, industry_keywords)]

    # ----------------------------
    # 4) SQLite保存（履歴）
    # ----------------------------
    conn = get_conn()
    init_db(conn)

    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for it in items:
        # ★変更点：dateが空なら None（= SQLiteではNULL）
        d = (it.get("date") or "").strip()
        rows.append({
            "id": make_id_from_url(it["url"]),
            "date": d if d else None,
            "source": it.get("source", ""),
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "category": it.get("category", ""),
            "created_at": now_iso,
        })

    inserted = upsert_articles(conn, rows)
    print(f"DB inserted: {inserted} new rows")

    # ----------------------------
    # 5) 集計 & ダッシュボード更新
    # ----------------------------
    payload = query_daily_counts(conn, days=30)
    write_daily_counts(payload)
    write_dashboard_html()

    kw = compute_keywords(conn, days=30)
    write_keywords(kw)

    print("Dashboard & analytics updated")

    # ----------------------------
    # 6) Discord用メッセージ作成
    # ----------------------------
    top_items = pick_top(items, n=top_n)

    if use_ai:
        try:
            ai_items = pick_top(items, n=min(10, len(items)))
            message = summarize_with_openai_jp(industry, ai_items)
        except Exception as e:
            message = build_basic_message(industry, top_items, total_items=len(items))
            message += f"\n\n（AI要約エラーのため簡易版）\n{e}"
    else:
        message = build_basic_message(industry, top_items, total_items=len(items))

    dashboard_url = os.environ.get("DASHBOARD_URL", "").strip()
    if dashboard_url:
        message += f"\n\n📊 ダッシュボード: {dashboard_url}"

    # 7) post to Discord
    post_to_discord_safe(webhook_url, message)
    print("Posted to Discord successfully.")


if __name__ == "__main__":
    main()
