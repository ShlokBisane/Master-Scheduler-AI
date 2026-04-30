"""
SQLite Database Layer for Master Scheduler AI
Tables: users, chats, messages, schedules, settings, subject_colors
"""

import sqlite3
import json
import os
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "master_scheduler.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                gemini_api_key TEXT DEFAULT '',
                openrouter_api_key TEXT DEFAULT '',
                active_provider TEXT DEFAULT 'gemini',
                user_name TEXT DEFAULT '',
                user_type TEXT DEFAULT 'student',
                profile_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT DEFAULT 'New Chat',
                mode TEXT DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                schedule_json TEXT,
                confirmed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                subject TEXT NOT NULL,
                color TEXT DEFAULT '#4A90D9',
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                session_type TEXT DEFAULT 'study',
                topic TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS subject_colors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT UNIQUE NOT NULL,
                color TEXT NOT NULL DEFAULT '#4A90D9',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            INSERT OR IGNORE INTO settings (id) VALUES (1);
        """)


# ─── Settings ───────────────────────────────────────────────

def get_settings():
    with get_db() as conn:
        row = conn.execute("SELECT * FROM settings WHERE id=1").fetchone()
        if row:
            return dict(row)
        return None


def update_settings(**kwargs):
    allowed = ['gemini_api_key', 'openrouter_api_key', 'active_provider',
               'user_name', 'user_type', 'profile_json']
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values())
    with get_db() as conn:
        conn.execute(
            f"UPDATE settings SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE id=1",
            values
        )


# ─── Profile ────────────────────────────────────────────────

def get_profile():
    """Get user profile data."""
    settings = get_settings()
    if settings and settings.get('profile_json'):
        try:
            profile = json.loads(settings['profile_json'])
            profile['name'] = settings.get('user_name', '')
            profile['user_type'] = settings.get('user_type', 'student')
            return profile
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        'name': settings.get('user_name', '') if settings else '',
        'user_type': settings.get('user_type', 'student') if settings else 'student'
    }


def save_profile(profile_data: dict):
    """Save user profile data."""
    name = profile_data.pop('name', '')
    user_type = profile_data.pop('user_type', 'student')
    profile_json = json.dumps(profile_data)
    update_settings(
        user_name=name,
        user_type=user_type,
        profile_json=profile_json
    )


# ─── Chats ──────────────────────────────────────────────────

def create_chat(title="New Chat", mode="student"):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO chats (title, mode) VALUES (?, ?)",
            (title, mode)
        )
        return cursor.lastrowid


def get_all_chats():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM chats ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_chat(chat_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
        return dict(row) if row else None


def update_chat_title(chat_id, title):
    with get_db() as conn:
        conn.execute(
            "UPDATE chats SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (title, chat_id)
        )


def delete_chat(chat_id):
    with get_db() as conn:
        conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))


# ─── Messages ───────────────────────────────────────────────

def add_message(chat_id, role, content, schedule_json=None):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (chat_id, role, content, schedule_json) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, json.dumps(schedule_json) if schedule_json else None)
        )
        conn.execute(
            "UPDATE chats SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (chat_id,)
        )
        return cursor.lastrowid


def get_messages(chat_id, limit=100):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE chat_id=? ORDER BY created_at ASC LIMIT ?",
            (chat_id, limit)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get('schedule_json'):
                try:
                    d['schedule_json'] = json.loads(d['schedule_json'])
                except:
                    pass
            result.append(d)
        return result


def confirm_schedule_message(message_id):
    with get_db() as conn:
        conn.execute(
            "UPDATE messages SET confirmed=1 WHERE id=?",
            (message_id,)
        )


# ─── Schedules ──────────────────────────────────────────────

def add_schedule(chat_id, subject, color, date_str, start_time, end_time,
                 session_type="study", topic="", priority=3):
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO schedules 
               (chat_id, subject, color, date, start_time, end_time, session_type, topic, priority)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (chat_id, subject, color, date_str, start_time, end_time,
             session_type, topic, priority)
        )
        # Also update subject_colors table
        conn.execute(
            """INSERT INTO subject_colors (subject, color) VALUES (?, ?)
               ON CONFLICT(subject) DO UPDATE SET color=excluded.color, updated_at=CURRENT_TIMESTAMP""",
            (subject, color)
        )
        return cursor.lastrowid


def get_schedules_for_date(date_str):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE date=? ORDER BY start_time ASC",
            (date_str,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_calendar_events():
    """Get all dates that have scheduled events with their subject colors.
       Excludes breaks from dot display. Marks exam dates."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT date, subject, color, session_type, COUNT(*) as count
               FROM schedules 
               GROUP BY date, subject, color, session_type
               ORDER BY date ASC"""
        ).fetchall()
        # Group by date
        calendar = {}
        for r in rows:
            d = dict(r)
            dt = d['date']
            if dt not in calendar:
                calendar[dt] = {"subjects": [], "has_exam": False}
            
            # Only add non-break sessions as dots
            if d['session_type'] not in ('break',):
                calendar[dt]["subjects"].append({
                    'subject': d['subject'],
                    'color': d['color'],
                    'type': d['session_type'],
                    'count': d['count']
                })
            
            # Mark exam dates
            if d['session_type'] in ('exam', 'test', 'mock'):
                calendar[dt]["has_exam"] = True
        
        return calendar


def get_today_tasks():
    """Get today's tasks including nearby dates for context."""
    today = date.today().isoformat()
    with get_db() as conn:
        # Today's tasks
        rows = conn.execute(
            "SELECT * FROM schedules WHERE date=? ORDER BY start_time ASC",
            (today,)
        ).fetchall()
        tasks = [dict(r) for r in rows]
        
        # Count by status
        pending = sum(1 for t in tasks if t['status'] == 'pending')
        completed = sum(1 for t in tasks if t['status'] == 'completed')
        in_progress = sum(1 for t in tasks if t['status'] == 'in_progress')
        missed = sum(1 for t in tasks if t['status'] == 'missed')
        
        # Get overdue tasks from past dates
        overdue_rows = conn.execute(
            "SELECT * FROM schedules WHERE date < ? AND status='pending' AND session_type != 'break' ORDER BY date ASC, start_time ASC",
            (today,)
        ).fetchall()
        overdue = [dict(r) for r in overdue_rows]
        
        # Get next upcoming task
        next_task = None
        for t in tasks:
            if t['status'] == 'pending' and t['session_type'] != 'break':
                next_task = t
                break
        
        return {
            "tasks": tasks,
            "overdue": overdue,
            "next_task": next_task,
            "stats": {
                "total": len(tasks),
                "pending": pending,
                "completed": completed,
                "in_progress": in_progress,
                "missed": missed,
            }
        }


def update_task_status(task_id, status):
    with get_db() as conn:
        conn.execute(
            "UPDATE schedules SET status=? WHERE id=?",
            (status, task_id)
        )


def get_all_schedules():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM schedules ORDER BY date ASC, start_time ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_schedules_for_chat(chat_id):
    with get_db() as conn:
        conn.execute("DELETE FROM schedules WHERE chat_id=?", (chat_id,))


def delete_schedules_by_subject(subject: str):
    """Delete all schedules for a specific subject."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM schedules WHERE subject=?",
            (subject,)
        )


def delete_schedule_by_date_and_subject(date_str: str, subject: str):
    """Delete all schedules for a specific subject on a specific date."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM schedules WHERE date=? AND subject=?",
            (date_str, subject)
        )


def delete_schedule_by_id(schedule_id: int):
    """Delete a specific schedule entry by ID."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM schedules WHERE id=?",
            (schedule_id,)
        )


# ─── Subject Colors ─────────────────────────────────────────

def get_subject_colors():
    """Get all subject → color mappings."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT subject, color FROM subject_colors ORDER BY subject ASC"
        ).fetchall()
        return {r['subject']: r['color'] for r in rows}


def update_subject_color(subject: str, new_color: str):
    """Update a subject's color globally (in subject_colors table AND all schedules)."""
    with get_db() as conn:
        # Update the color mapping
        conn.execute(
            """INSERT INTO subject_colors (subject, color) VALUES (?, ?)
               ON CONFLICT(subject) DO UPDATE SET color=excluded.color, updated_at=CURRENT_TIMESTAMP""",
            (subject, new_color)
        )
        # Update ALL existing schedule entries for this subject
        conn.execute(
            "UPDATE schedules SET color=? WHERE subject=?",
            (new_color, subject)
        )


def get_stress_data():
    """Calculate stress metrics based on schedule density and completion."""
    today = date.today().isoformat()
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as c FROM schedules WHERE date >= ? AND session_type != 'break'", (today,)
        ).fetchone()['c']
        
        completed = conn.execute(
            "SELECT COUNT(*) as c FROM schedules WHERE status='completed'"
        ).fetchone()['c']
        
        missed = conn.execute(
            "SELECT COUNT(*) as c FROM schedules WHERE status='missed'"
        ).fetchone()['c']
        
        pending = conn.execute(
            "SELECT COUNT(*) as c FROM schedules WHERE status='pending' AND date < ? AND session_type != 'break'",
            (today,)
        ).fetchone()['c']
        
        # Overdue tasks that are still pending
        overdue = pending
        
        total_all = conn.execute(
            "SELECT COUNT(*) as c FROM schedules WHERE session_type != 'break'"
        ).fetchone()['c']
        
        if total_all == 0:
            return {"score": 0, "level": "green", "label": "No tasks yet",
                    "total": 0, "completed": 0, "missed": 0, "overdue": 0, "upcoming": total}
        
        # Stress score: higher = more stressed
        # Based on: missed tasks, overdue tasks, and upcoming density
        stress = min(100, int(((missed + overdue) / max(total_all, 1)) * 100))
        
        if stress < 30:
            level = "green"
            label = "You're on track! 🎯"
        elif stress < 60:
            level = "yellow" 
            label = "Falling behind slightly ⚠️"
        else:
            level = "red"
            label = "Schedule overload! 🔴"
        
        return {
            "score": stress,
            "level": level,
            "label": label,
            "total": total_all,
            "completed": completed,
            "missed": missed,
            "overdue": overdue,
            "upcoming": total
        }


# Initialize on import
init_db()
