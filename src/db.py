# db.py
import sqlite3
from typing import Dict, List, Any
from pathlib import Path

DB_PATH = Path("data/news.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  date TEXT,                 -- YYYY-MM-DD or NULL
  source TEXT,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  category TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
"""

def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()

def upsert_articles(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> int:
    sql = """
    INSERT OR IGNORE INTO articles
    (id, date, source, title, url, category, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    cur = conn.cursor()
    before = conn.total_changes

    cur.executemany(sql, [
        (
            r["id"],
            r["date"] if r.get("date") else None,  # ★ 空文字を NULL に
            r.get("source", ""),
            r.get("title", ""),
            r.get("url", ""),
            r.get("category", ""),
            r.get("created_at", ""),
        )
        for r in rows
    ])
    conn.commit()

    return conn.total_changes - before
