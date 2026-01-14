# import sqlite3
# import pandas as pd
# from pathlib import Path

# DB_PATH = Path("data/news.db")
# OUT_DIR = Path("docs/exports")
# OUT_FILE = OUT_DIR / "articles.xlsx"

# def export_excel():
#     OUT_DIR.mkdir(parents=True, exist_ok=True)

#     conn = sqlite3.connect(DB_PATH)
#     df = pd.read_sql_query(
#         """
#         SELECT
#           date,
#           source,
#           title,
#           url,
#           category,
#           created_at
#         FROM articles
#         ORDER BY date DESC
#         """,
#         conn
#     )
#     conn.close()

#     df.to_excel(OUT_FILE, index=False)
#     print(f"Excel exported to {OUT_FILE}")

# if __name__ == "__main__":
#     export_excel()


# src/export_excel.py
import sqlite3
from pathlib import Path
import pandas as pd

# 既存DBパス（あなたの構成に合わせて固定）
DB_PATH = Path("data/news.db")

EXPORT_DIR = Path("docs/exports")

# 4パターン
EXPORT_RANGES = [
    (30, "articles_30d.xlsx"),
    (90, "articles_90d.xlsx"),
    (365, "articles_1y.xlsx"),
    (1095, "articles_3y.xlsx"),
]


def export_articles_excel(conn: sqlite3.Connection, days: int, out_path: Path) -> None:
    """
    直近 days 日分の記事をExcelに出力する（単体機能）
    """
    window = f"-{days} day"

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
        WHERE date IS NOT NULL
          AND date >= date('now', ?)
        ORDER BY date DESC
        """,
        conn,
        params=(window,),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False)
    print(f"Excel exported: {out_path}")


def export_excel(conn: sqlite3.Connection | None = None) -> None:
    """
    main.py から呼ばれる入口（互換維持）
    - conn を渡されたらそれを使う
    - 渡されなければ DB_PATH から自分で接続する
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    own_conn = None
    try:
        if conn is None:
            own_conn = sqlite3.connect(DB_PATH)
            conn_to_use = own_conn
        else:
            conn_to_use = conn

        for days, filename in EXPORT_RANGES:
            export_articles_excel(conn_to_use, days, EXPORT_DIR / filename)

    finally:
        if own_conn is not None:
            own_conn.close()


if __name__ == "__main__":
    export_excel()
