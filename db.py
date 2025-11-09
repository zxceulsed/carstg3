# db.py
import sqlite3

DB_NAME = "cars.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            custom_link TEXT
        )
    """)

    # вставляем строку, если её нет
    cur.execute("INSERT OR IGNORE INTO config (id, custom_link) VALUES (1, NULL)")

def ad_exists(link: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM ads WHERE link = ?", (link,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def add_ad(link: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO ads (link) VALUES (?)", (link,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # уже есть
    conn.close()


# db.py
def set_custom_link(link: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # гарантированно заменяет строку, даже если её нет
    cur.execute("INSERT OR REPLACE INTO config (id, custom_link) VALUES (1, ?)", (link,))
    conn.commit()
    conn.close()


def get_custom_link() -> str | None:
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT custom_link FROM config WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
