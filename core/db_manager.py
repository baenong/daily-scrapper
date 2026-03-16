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
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


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
                    description TEXT,           
                    is_completed INTEGER DEFAULT 0,
                    is_loadmap INTEGER DEFAULT 0 -- 중요일정 로드맵
                )
                """
            )

            # 2026. 3. 10. 정책브리핑
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    rss_url TEXT NOT NULL,
                    is_checked INTEGER DEFAULT 1
                )
                """
            )

            count = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
            if count == 0:
                # ※ korea.kr의 실제 RSS 주소 체계에 맞춰 추후 자유롭게 수정하시면 됩니다.
                default_departments = [
                    ("정책뉴스", "https://www.korea.kr/rss/policy.xml"),
                    ("보도자료", "https://www.korea.kr/rss/pressrelease.xml"),
                    ("행정안전부", "https://www.korea.kr/rss/dept_mois.xml"),
                    ("인사혁신처", "https://www.korea.kr/rss/dept_mpm.xml"),
                    ("국무조정실", "https://www.korea.kr/rss/dept_opm.xml"),
                    ("재정경제부", "https://www.korea.kr/rss/dept_moef.xml"),
                    ("과학기술정보통신부", "https://www.korea.kr/rss/dept_msit.xml"),
                    ("교육부", "https://www.korea.kr/rss/dept_moe.xml"),
                    ("외교부", "https://www.korea.kr/rss/dept_mofa.xml"),
                    ("통일부", "https://www.korea.kr/rss/dept_unikorea.xml"),
                    ("법무부", "https://www.korea.kr/rss/dept_moj.xml"),
                    ("국방부", "https://www.korea.kr/rss/dept_mnd.xml"),
                    ("국가보훈부", "https://www.korea.kr/rss/dept_mpva.xml"),
                    ("문화체육관광부", "https://www.korea.kr/rss/dept_mcst.xml"),
                    ("농림축산식품부", "https://www.korea.kr/rss/dept_mafra.xml"),
                    ("산업통상부", "https://www.korea.kr/rss/dept_motir.xml"),
                    ("보건복지부", "https://www.korea.kr/rss/dept_mw.xml"),
                    ("기후에너지환경부", "https://www.korea.kr/rss/dept_mcee.xml"),
                    ("고용노동부", "https://www.korea.kr/rss/dept_moel.xml"),
                    ("성평등가족부", "https://www.korea.kr/rss/dept_mogef.xml"),
                    ("국토교통부", "https://www.korea.kr/rss/dept_molit.xml"),
                    ("해양수산부", "https://www.korea.kr/rss/dept_mof.xml"),
                    ("중소벤처기업부", "https://www.korea.kr/rss/dept_mss.xml"),
                    ("기획예산처", "https://www.korea.kr/rss/dept_mpb.xml"),
                    ("식품의약품안전처", "https://www.korea.kr/rss/dept_mfds.xml"),
                    ("국가데이터처", "https://www.korea.kr/rss/dept_mods.xml"),
                ]
                conn.executemany(
                    "INSERT INTO departments (name, rss_url, is_checked) VALUES (?, ?, 0)",
                    default_departments,
                )

            # Setting
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )


def add_schedule(
    title,
    start_date,
    end_date,
    repeat_type,
    repeat_end,
    color,
    description,
    is_completed=False,
    is_loadmap=False,
):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO schedules (
                    title, start_date, end_date, 
                    repeat_type, repeat_end, 
                    color, description, 
                    is_completed, is_loadmap
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    start_date,
                    end_date,
                    repeat_type,
                    repeat_end,
                    color,
                    description,
                    int(is_completed),
                    int(is_loadmap),
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
    description,
    is_completed,
    is_loadmap,
):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                UPDATE schedules SET 
                    title=?, start_date=?, end_date=?, 
                    repeat_type=?, repeat_end=?, 
                    color=?, description=?, 
                    is_completed=?, is_loadmap=? 
                WHERE id=?
                """,
                (
                    title,
                    start_date,
                    end_date,
                    repeat_type,
                    repeat_end,
                    color,
                    description,
                    int(is_completed),
                    int(is_loadmap),
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
            """
            SELECT id, title, start_date, end_date, 
                repeat_type, repeat_end,
                color, description,
                is_completed, is_loadmap
            FROM schedules
            """
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "start_date": r["start_date"],
                "end_date": r["end_date"],
                "repeat_type": r["repeat_type"],
                "repeat_end": r["repeat_end"],
                "color": r["color"],
                "description": r["description"],
                "is_completed": bool(r["is_completed"]),
                "is_loadmap": bool(r["is_loadmap"]),
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
        return [{"text": r["keyword"], "checked": bool(r["is_active"])} for r in rows]


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
        return [{"text": r["keyword"], "checked": bool(r["is_active"])} for r in rows]


def load_departments():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT id, name, rss_url, is_checked FROM departments"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "rss_url": r["rss_url"],
                "checked": bool(r["is_checked"]),
            }
            for r in rows
        ]


def update_department_status(dept_id, is_checked):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "UPDATE departments SET is_checked = ? WHERE id = ?",
                (int(is_checked), dept_id),
            )


def get_setting(key, default_value=None):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default_value


def set_setting(key, value):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
