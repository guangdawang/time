""" 数据库初始化与所有数据访问操作 """

import sqlite3
from datetime import date

DB_NAME = "tasks.db"


def _today_str():
    """返回当天的 ISO 日期字符串 (YYYY-MM-DD)"""
    return date.today().isoformat()


def init_db():
    """创建表并清理过期重点记录"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            tag TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_focus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            focus_date TEXT NOT NULL,
            sort_order INTEGER NOT NULL CHECK(sort_order BETWEEN 1 AND 3),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            UNIQUE(focus_date, task_id),
            UNIQUE(focus_date, sort_order)
        )
    ''')
    # 清理旧日期的重点记录
    today = _today_str()
    c.execute("DELETE FROM daily_focus WHERE focus_date < ?", (today,))
    conn.commit()
    conn.close()


def fetch_tasks(status_filter="all"):
    """查询任务，同时获取今日重点信息（sort_order，若无则为 NULL）"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = _today_str()
    base_query = """
        SELECT t.id, t.title, t.tag, t.status, df.sort_order
        FROM tasks t
        LEFT JOIN daily_focus df ON t.id = df.task_id AND df.focus_date = ?
    """
    params = [today]
    if status_filter == "pending":
        base_query += " WHERE t.status='pending'"
    elif status_filter == "done":
        base_query += " WHERE t.status='done'"

    base_query += """
        ORDER BY CASE WHEN df.sort_order IS NULL THEN 1 ELSE 0 END,
                 df.sort_order ASC,
                 t.id DESC
    """
    c.execute(base_query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def add_task(title, tag):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, tag) VALUES (?, ?)", (title, tag))
    conn.commit()
    conn.close()


def update_task(task_id, title, tag):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE tasks SET title=?, tag=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
              (title, tag, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def toggle_status(task_id, current_status):
    new_status = "done" if current_status == "pending" else "pending"
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
              (new_status, task_id))
    conn.commit()
    conn.close()


def get_all_tags():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT tag FROM tasks WHERE tag != ''")
    rows = c.fetchall()
    conn.close()
    tags_set = set()
    for (tag_str,) in rows:
        for t in tag_str.split(","):
            t = t.strip()
            if t:
                tags_set.add(t)
    return sorted(tags_set, key=str.lower)


# ---------- 每日重点操作 ----------
def get_today_focus_count():
    today = _today_str()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM daily_focus WHERE focus_date = ?", (today,))
    count = c.fetchone()[0]
    conn.close()
    return count


def get_today_focus_tasks():
    """返回今日重点列表（task_id, sort_order）"""
    today = _today_str()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT task_id, sort_order FROM daily_focus WHERE focus_date = ? ORDER BY sort_order",
              (today,))
    tasks = c.fetchall()
    conn.close()
    return tasks


def add_focus(task_id, sort_order):
    """将任务设为今日重点，若序号被占用则报错"""
    today = _today_str()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO daily_focus (task_id, focus_date, sort_order) VALUES (?, ?, ?)",
                  (task_id, today, sort_order))
        conn.commit()
        success = True
        msg = ""
    except sqlite3.IntegrityError as e:
        conn.rollback()
        success = False
        if "UNIQUE constraint failed: daily_focus.focus_date, daily_focus.sort_order" in str(e):
            msg = f"优先级 {sort_order} 已被占用，请先调整顺序或选择其他优先级。"
        elif "UNIQUE constraint failed: daily_focus.focus_date, daily_focus.task_id" in str(e):
            msg = "该任务已经是今日重点。"
        else:
            msg = "操作失败，请重试。"
    finally:
        conn.close()
    return success, msg


def remove_focus(task_id):
    today = _today_str()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM daily_focus WHERE focus_date = ? AND task_id = ?", (today, task_id))
    conn.commit()
    conn.close()


def is_task_focus(task_id):
    today = _today_str()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT sort_order FROM daily_focus WHERE focus_date = ? AND task_id = ?",
              (today, task_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None