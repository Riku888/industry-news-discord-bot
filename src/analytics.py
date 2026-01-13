# analytics.py
import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from datetime import datetime

OUT_DAILY = Path("docs/data/daily_counts.json")
OUT_KEYWORDS = Path("docs/data/top_keywords.json")

# ----------------------------
# 日別集計（date IS NOT NULL のみ）
# ----------------------------
def query_daily_counts(conn: sqlite3.Connection, days: int = 30) -> Dict[str, Any]:
    window = f"-{days} day"

    sql_total = """
    SELECT date, COUNT(*) as cnt
    FROM articles
    WHERE date IS NOT NULL
      AND date >= date('now', ?)
    GROUP BY date
    ORDER BY date ASC
    """

    sql_cat = """
    SELECT date, category, COUNT(*) as cnt
    FROM articles
    WHERE date IS NOT NULL
      AND date >= date('now', ?)
    GROUP BY date, category
    ORDER BY date ASC
    """

    sql_src = """
    SELECT date, source, COUNT(*) as cnt
    FROM articles
    WHERE date IS NOT NULL
      AND date >= date('now', ?)
    GROUP BY date, source
    ORDER BY date ASC
    """

    total = conn.execute(sql_total, (window,)).fetchall()
    cat = conn.execute(sql_cat, (window,)).fetchall()
    src = conn.execute(sql_src, (window,)).fetchall()

    dates = sorted({r[0] for r in total})

    total_map = {d: 0 for d in dates}
    for d, c in total:
        total_map[d] = c

    cat_map: Dict[str, Dict[str, int]] = {d: {} for d in dates}
    for d, category, c in cat:
        cat_map[d][category or "未分類"] = c

    src_map: Dict[str, Dict[str, int]] = {d: {} for d in dates}
    for d, source, c in src:
        src_map[d][source or "不明"] = c

    return {
        "dates": dates,
        "total": [total_map[d] for d in dates],
        "by_category": cat_map,
        "by_source": src_map,
    }

def write_daily_counts(payload: Dict[str, Any]) -> None:
    OUT_DAILY.parent.mkdir(parents=True, exist_ok=True)
    OUT_DAILY.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# ----------------------------
# キーワード分析（date IS NOT NULL）
# ----------------------------
def compute_keywords(conn: sqlite3.Connection, days: int = 30) -> Dict[str, Any]:
    STOP = {
        "the","a","an","to","of","in","on","for","and","or","with",
        "from","by","as","is","are","was","were"
    }

    def tokenize(text: str) -> List[str]:
        return [
            w for w in re.findall(r"[a-zA-Z0-9\\-]{3,}", text.lower())
            if w not in STOP
        ]

    today = datetime.utcnow().strftime("%Y-%m-%d")

    rows_today = conn.execute(
        "SELECT title FROM articles WHERE date = ?",
        (today,)
    ).fetchall()

    rows_past = conn.execute(
        """
        SELECT title FROM articles
        WHERE date IS NOT NULL
          AND date >= date('now', ?)
          AND date < date('now')
        """,
        (f"-{days} day",)
    ).fetchall()

    c_today = Counter()
    for (t,) in rows_today:
        c_today.update(tokenize(t or ""))

    c_past = Counter()
    for (t,) in rows_past:
        c_past.update(tokenize(t or ""))

    top_today = c_today.most_common(20)

    rising = []
    for (w, n) in top_today:
        base = c_past[w] / max(days, 1)
        score = n / (base + 0.5)
        rising.append((w, n, round(score, 2)))

    rising.sort(key=lambda x: x[2], reverse=True)

    return {
        "date": today,
        "top_today": top_today,
        "rising": rising[:10],
    }

def write_keywords(payload: Dict[str, Any]) -> None:
    OUT_KEYWORDS.parent.mkdir(parents=True, exist_ok=True)
    OUT_KEYWORDS.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
