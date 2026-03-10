import sqlite3
import os
import sys

from contextlib import closing


def get_db_path():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, "data.db")


def get_connection():
    return sqlite3.connect(get_db_path())


def init_db():
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS news_keywords (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keyword TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1
                )                   
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS law_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
                """
            )

            # 2026. 3. 4. 신규 스케쥴러
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_date TEXT NOT NULL,  
                    end_date TEXT NOT NULL,    
                    repeat_type TEXT DEFAULT 'none', 
                    repeat_end TEXT,           
                    color TEXT DEFAULT '#2196F3',
                    is_completed INTEGER DEFAULT 0 -- 완료 여부 추가
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )


def add_schedule(
    title, start_date, end_date, repeat_type, repeat_end, color, is_completed=False
):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO schedules (title, start_date, end_date, repeat_type, repeat_end, color, is_completed) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    title,
                    start_date,
                    end_date,
                    repeat_type,
                    repeat_end,
                    color,
                    int(is_completed),
                ),
            )


def update_schedule(
    schedule_id,
    title,
    start_date,
    end_date,
    repeat_type,
    repeat_end,
    color,
    is_completed,
):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "UPDATE schedules SET title=?, start_date=?, end_date=?, repeat_type=?, repeat_end=?, color=?, is_completed=? WHERE id=?",
                (
                    title,
                    start_date,
                    end_date,
                    repeat_type,
                    repeat_end,
                    color,
                    int(is_completed),
                    schedule_id,
                ),
            )


def delete_schedule(schedule_id):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))


def get_schedules():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT id, title, start_date, end_date, repeat_type, repeat_end, color, is_completed FROM schedules"
        ).fetchall()
        return [
            {
                "id": r[0],
                "title": r[1],
                "start_date": r[2],
                "end_date": r[3],
                "repeat_type": r[4],
                "repeat_end": r[5],
                "color": r[6],
                "is_completed": bool(r[7]),
            }
            for r in rows
        ]


# Keyword Functions
def save_news_keywords(keywords_list):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM news_keywords")
            data_to_insert = [(kw["text"], int(kw["checked"])) for kw in keywords_list]
            conn.executemany(
                "INSERT INTO news_keywords (keyword, is_active) VALUES (?, ?)",
                data_to_insert,
            )


def load_news_keywords():
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT keyword, is_active FROM news_keywords").fetchall()
        return [{"text": r[0], "checked": bool(r[1])} for r in rows]


def save_law_keywords(laws_list):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM law_keywords")
            data_to_insert = [(law["text"], int(law["checked"])) for law in laws_list]
            conn.executemany(
                "INSERT INTO law_keywords (keyword, is_active) VALUES (?, ?)",
                data_to_insert,
            )


def load_law_keywords():
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT keyword, is_active FROM law_keywords").fetchall()
        return [{"text": r[0], "checked": bool(r[1])} for r in rows]


def get_setting(key, default_value=None):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default_value


def set_setting(key, value):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
