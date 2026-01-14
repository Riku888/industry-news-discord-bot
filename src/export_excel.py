import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/news.db")
OUT_DIR = Path("docs/exports")
OUT_FILE = OUT_DIR / "articles.xlsx"

def export_excel():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT
          date,
          source,
          title,
          url,
          category,
          created_at
        FROM articles
        ORDER BY date DESC
        """,
        conn
    )
    conn.close()

    df.to_excel(OUT_FILE, index=False)
    print(f"Excel exported to {OUT_FILE}")

if __name__ == "__main__":
    export_excel()
