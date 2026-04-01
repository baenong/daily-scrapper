import sqlite3
import os
import sys
from contextlib import closing

# Constants
CAT_GOV = "정부부처"
CAT_MEDIA = "언론사"
GROUP_UNASSIGNED = "미지정"


def get_db_path():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, "data.db")


def get_connection():
    conn = sqlite3.connect(get_db_path(), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    with closing(get_connection()) as conn:
        with conn:
            current_version = conn.execute("PRAGMA user_version").fetchone()[0]

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
                    repeat_rule TEXT,
                    repeat_end TEXT,
                    color TEXT DEFAULT '#2196F3',
                    description TEXT,           
                    is_completed INTEGER DEFAULT 0,
                    is_roadmap INTEGER DEFAULT 0,
                    group_id INTEGER
                )
                """
            )

            # 2026. 3. 16. 로드맵 작성을 위한 그룹 테이블
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS roadmap_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    color TEXT DEFAULT '#2196F3'
                )
                """
            )

            # 정책브리핑
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    rss_url TEXT NOT NULL,
                    is_checked INTEGER DEFAULT 1,
                    category TEXT DEFAULT '정부부처'
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_colors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    hex_code TEXT NOT NULL
                )
                """
            )

            # v1.03 Version Migration
            if current_version < 1:

                # Departments Table Migration (Category)
                cursor = conn.execute("PRAGMA table_info(departments)")
                columns = [info[1] for info in cursor.fetchall()]

                if "category" not in columns:
                    conn.execute(
                        f"ALTER TABLE departments ADD COLUMN category TEXT DEFAULT '{CAT_GOV}'",
                    )

                # Schedule Table Migration (Description, RoadMap)
                cursor = conn.execute("PRAGMA table_info(schedules)")
                columns = [info[1] for info in cursor.fetchall()]
                if "description" not in columns:
                    conn.execute("ALTER TABLE schedules ADD COLUMN description TEXT")

                if "is_roadmap" not in columns:
                    conn.execute(
                        "ALTER TABLE schedules ADD COLUMN is_roadmap INTEGER DEFAULT 0"
                    )

                if "group_id" not in columns:
                    conn.execute("ALTER TABLE schedules ADD COLUMN group_id INTEGER")

                conn.execute("PRAGMA user_version = 1")

            # v1.04 Version Migration
            if current_version < 2:
                cursor = conn.execute("PRAGMA table_info(schedules)")
                columns = [info[1] for info in cursor.fetchall()]
                if "repeat_rule" not in columns:
                    conn.execute("ALTER TABLE schedules ADD COLUMN repeat_rule TEXT")

                conn.execute("PRAGMA user_version = 2")

            # ==========================================================================
            # Input Default Value
            # ==========================================================================
            unassigned_count = conn.execute(
                "SELECT COUNT(*) FROM roadmap_groups WHERE name=?",
                (GROUP_UNASSIGNED,),
            ).fetchone()[0]
            if unassigned_count == 0:
                conn.execute(
                    "INSERT INTO roadmap_groups (name, color) VALUES (?, '#A8A8A8')",
                    (GROUP_UNASSIGNED,),
                )

            count = conn.execute(
                "SELECT COUNT(*) FROM departments WHERE category = ?", (CAT_GOV,)
            ).fetchone()[0]

            if count == 0:
                # ※ korea.kr의 RSS 주소
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
                    "INSERT INTO departments (name, rss_url, is_checked, category) VALUES (?, ?, 0, ?)",
                    [(*dept, CAT_GOV) for dept in default_departments],
                )

            media_count = conn.execute(
                "SELECT COUNT(*) FROM departments WHERE category = ?", (CAT_MEDIA,)
            ).fetchone()[0]
            if media_count == 0:
                default_media = [
                    ("전북일보", "https://www.jjan.kr/news/rssAll"),
                ]
                conn.executemany(
                    "INSERT INTO departments (name, rss_url, is_checked, category) VALUES (?, ?, 0, ?)",
                    [(*media, CAT_MEDIA) for media in default_media],
                )


def add_schedule(
    title,
    start_date,
    end_date,
    repeat_type,
    repeat_rule,
    repeat_end,
    color,
    description,
    is_completed=False,
    is_roadmap=False,
    group_id=None,
):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO schedules (
                    title, start_date, end_date, 
                    repeat_type, repeat_rule, repeat_end, 
                    color, description, 
                    is_completed, is_roadmap, group_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    start_date,
                    end_date,
                    repeat_type,
                    repeat_rule,
                    repeat_end,
                    color,
                    description,
                    int(is_completed),
                    int(is_roadmap),
                    group_id,
                ),
            )


def update_schedule(
    schedule_id,
    title,
    start_date,
    end_date,
    repeat_type,
    repeat_rule,
    repeat_end,
    color,
    description,
    is_completed,
    is_roadmap=False,
    group_id=None,
):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                UPDATE schedules SET 
                    title=?, start_date=?, end_date=?, 
                    repeat_type=?, repeat_rule=?, repeat_end=?, 
                    color=?, description=?, 
                    is_completed=?, is_roadmap=? , group_id=?
                WHERE id=?
                """,
                (
                    title,
                    start_date,
                    end_date,
                    repeat_type,
                    repeat_rule,
                    repeat_end,
                    color,
                    description,
                    int(is_completed),
                    int(is_roadmap),
                    group_id,
                    schedule_id,
                ),
            )


def delete_schedule(schedule_id):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))


def delete_non_roadmap_schedules():
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM schedules WHERE is_roadmap = 0")


def get_schedules():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT id, title, start_date, end_date, 
                repeat_type, repeat_rule, repeat_end,
                color, description,
                is_completed, is_roadmap, group_id
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
                "repeat_rule": r["repeat_rule"],
                "repeat_end": r["repeat_end"],
                "color": r["color"],
                "description": r["description"],
                "is_completed": bool(r["is_completed"]),
                "is_roadmap": bool(r["is_roadmap"]),
                "group_id": r["group_id"],
            }
            for r in rows
        ]


# Keyword Functions
def _save_keywords(table_name, items_list):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(f"DELETE FROM {table_name}")
            data_to_insert = [
                (item["text"], int(item["checked"])) for item in items_list
            ]
            conn.executemany(
                f"INSERT INTO {table_name} (keyword, is_active) VALUES (?, ?)",
                data_to_insert,
            )


def _load_keywords(table_name):
    with closing(get_connection()) as conn:
        rows = conn.execute(f"SELECT keyword, is_active FROM {table_name}").fetchall()
        return [{"text": r["keyword"], "checked": bool(r["is_active"])} for r in rows]


def save_news_keywords(keywords_list):
    _save_keywords("news_keywords", keywords_list)


def load_news_keywords():
    return _load_keywords("news_keywords")


def save_law_keywords(laws_list):
    _save_keywords("law_keywords", laws_list)


def load_law_keywords():
    return _load_keywords("law_keywords")


# Policy Brief
def load_departments(is_media=False):
    with closing(get_connection()) as conn:
        category_name = CAT_MEDIA if is_media else CAT_GOV

        rows = conn.execute(
            "SELECT id, name, rss_url, is_checked FROM departments WHERE category = ?",
            (category_name,),
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


def get_roadmap_groups():
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT id, name, color FROM roadmap_groups").fetchall()
        return [dict(r) for r in rows]


def add_roadmap_group(name, color):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO roadmap_groups (name, color) VALUES (?, ?)", (name, color)
            )


def update_roadmap_group(group_id, name, color):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "UPDATE roadmap_groups SET name=?, color=? WHERE id=?",
                (name, color, group_id),
            )


def delete_roadmap_group(group_id):
    with closing(get_connection()) as conn:
        with conn:
            row = conn.execute(
                "SELECT id FROM roadmap_groups WHERE name=?", (GROUP_UNASSIGNED,)
            ).fetchone()
            default_id = row[0] if row else None

            if default_id:
                conn.execute(
                    "UPDATE schedules SET group_id = ? WHERE group_id = ?",
                    (default_id, group_id),
                )
            else:
                conn.execute(
                    "UPDATE schedules SET group_id = NULL WHERE group_id = ?",
                    (group_id,),
                )

            conn.execute("DELETE FROM roadmap_groups WHERE id=?", (group_id,))


def add_custom_color(name, hex_code):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO custom_colors (name, hex_code) VALUES (?, ?)",
                (name, hex_code),
            )


def get_custom_colors():
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT name, hex_code FROM custom_colors").fetchall()
        return {r["name"]: r["hex_code"] for r in rows}


def delete_custom_color(name):
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM custom_colors WHERE name=?", (name,))
