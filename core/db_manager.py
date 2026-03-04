import sqlite3
import os
import sys


def get_db_path():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, "data.db")


def get_connection():
    return sqlite3.connect(get_db_path())


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS news_keywords (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   keyword TEXT NOT NULL,
                   is_active INTEGER DEFAULT 1
        )                   
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS law_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    # 2026. 3. 4. 신규 스케쥴러
    cursor.execute(
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def add_schedule(
    title, start_date, end_date, repeat_type, repeat_end, color, is_completed=False
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
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
    conn.commit()
    conn.close()


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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
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
    conn.commit()
    conn.close()


def delete_schedule(schedule_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
    conn.commit()
    conn.close()


def get_schedules():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, start_date, end_date, repeat_type, repeat_end, color, is_completed FROM schedules"
    )
    rows = cursor.fetchall()
    conn.close()
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM news_keywords")  # 기존 데이터 싹 비우기
    for kw in keywords_list:
        cursor.execute(
            "INSERT INTO news_keywords (keyword, is_active) VALUES (?, ?)",
            (kw["text"], int(kw["checked"])),
        )
    conn.commit()
    conn.close()


def load_news_keywords():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keyword, is_active FROM news_keywords")
    rows = cursor.fetchall()
    conn.close()
    return [{"text": r[0], "checked": bool(r[1])} for r in rows]


def save_law_keywords(laws_list):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM law_keywords")
    for law in laws_list:
        cursor.execute(
            "INSERT INTO law_keywords (keyword, is_active) VALUES (?, ?)",
            (law["text"], int(law["checked"])),
        )
    conn.commit()
    conn.close()


def load_law_keywords():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keyword, is_active FROM law_keywords")
    rows = cursor.fetchall()
    conn.close()
    return [{"text": r[0], "checked": bool(r[1])} for r in rows]


def get_setting(key, default_value=None):
    """DB에서 특정 설정값을 가져옵니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default_value


def set_setting(key, value):
    """DB에 설정값을 저장하거나 덮어씁니다 (INSERT OR REPLACE)."""
    conn = get_connection()
    cursor = conn.cursor()
    # 키가 이미 존재하면 값을 덮어쓰고, 없으면 새로 생성하는 강력한 SQL 문법입니다.
    cursor.execute(
        "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
        (key, str(value)),
    )
    conn.commit()
    conn.close()
