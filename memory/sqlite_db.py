import sqlite3
import time
import json
import os


class SQLiteMemoryManager:

    def __init__(self, db_path="memory/memory.db"):
        self.db_path = db_path

        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        self._init_db()

    # ====================================================
    # SCHEMA INIT
    # ====================================================

    def _init_db(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            goal TEXT,
            result TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            error TEXT,
            step TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            event TEXT
        )
        """)

        self.conn.commit()

    # ====================================================
    # TASK MEMORY
    # ====================================================

    def add_task(self, goal: str, result: dict):

        self.cursor.execute("""
        INSERT INTO tasks (timestamp, goal, result)
        VALUES (?, ?, ?)
        """, (
            time.time(),
            goal,
            json.dumps(result)
        ))

        self.conn.commit()

    def get_recent_tasks(self, limit=5):

        self.cursor.execute("""
        SELECT goal, result, timestamp
        FROM tasks
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = self.cursor.fetchall()

        return [
            {
                "goal": r[0],
                "result": json.loads(r[1]),
                "timestamp": r[2]
            }
            for r in rows
        ]

    # ====================================================
    # ERROR MEMORY
    # ====================================================

    def add_error(self, error: dict, step: dict = None):

        self.cursor.execute("""
        INSERT INTO errors (timestamp, error, step)
        VALUES (?, ?, ?)
        """, (
            time.time(),
            json.dumps(error),
            json.dumps(step) if step else None
        ))

        self.conn.commit()

    def get_recent_errors(self, limit=5):

        self.cursor.execute("""
        SELECT error, step, timestamp
        FROM errors
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = self.cursor.fetchall()

        return [
            {
                "error": json.loads(r[0]),
                "step": json.loads(r[1]) if r[1] else None,
                "timestamp": r[2]
            }
            for r in rows
        ]

    # ====================================================
    # EVENT MEMORY
    # ====================================================

    def add_event(self, event: dict):

        self.cursor.execute("""
        INSERT INTO events (timestamp, event)
        VALUES (?, ?)
        """, (
            time.time(),
            json.dumps(event)
        ))

        self.conn.commit()

    def get_recent_events(self, limit=5):

        self.cursor.execute("""
        SELECT event, timestamp
        FROM events
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = self.cursor.fetchall()

        return [
            {
                "event": json.loads(r[0]),
                "timestamp": r[1]
            }
            for r in rows
        ]

    # ====================================================
    # CONTEXT BUILDER (FOR PLANNER)
    # ====================================================

    def build_context(self):

        return {
            "recent_tasks": self.get_recent_tasks(),
            "recent_errors": self.get_recent_errors(),
            "recent_events": self.get_recent_events()
        }

    # ====================================================
    # SIMPLE SEARCH (LIGHTWEIGHT VERSION)
    # ====================================================

    def search_tasks(self, keyword: str):

        keyword = f"%{keyword.lower()}%"

        self.cursor.execute("""
        SELECT goal, result, timestamp
        FROM tasks
        WHERE LOWER(goal) LIKE ?
        ORDER BY id DESC
        """, (keyword,))

        rows = self.cursor.fetchall()

        return [
            {
                "goal": r[0],
                "result": json.loads(r[1]),
                "timestamp": r[2]
            }
            for r in rows
        ]

    # ====================================================
    # RESET (DEBUG TOOL)
    # ====================================================

    def clear(self):

        self.cursor.execute("DELETE FROM tasks")
        self.cursor.execute("DELETE FROM errors")
        self.cursor.execute("DELETE FROM events")

        self.conn.commit()

    # ====================================================
    # CLEAN SHUTDOWN
    # ====================================================

    def close(self):

        self.conn.commit()
        self.conn.close()
