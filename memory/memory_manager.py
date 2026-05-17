import json
import sqlite3
from datetime import datetime

from config.config import MEMORY_CONFIG


class MemoryManager:
    """
    Handles persistent memory storage for NextMind.

    Responsibilities:
    - Store completed steps
    - Store task summaries
    - Retrieve historical context
    - Manage SQLite persistence
    """

    def __init__(self):

        self.db_path = MEMORY_CONFIG.SQLITE_DB_PATH

        self._initialize_database()

    # ========================================================
    # DATABASE INITIALIZATION
    # ========================================================

    def _initialize_database(self):
        """
        Create required tables if they do not exist.
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ----------------------------------------------------
        # Task summaries
        # ----------------------------------------------------

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT,
            plan TEXT,
            created_at TEXT
        )
        """)

        # ----------------------------------------------------
        # Step execution history
        # ----------------------------------------------------

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS step_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT,
            step TEXT,
            result TEXT,
            created_at TEXT
        )
        """)

        conn.commit()
        conn.close()

    # ========================================================
    # STORE STEP RESULT
    # ========================================================

    def store_step_result(
        self,
        goal: str,
        step: dict,
        result: dict
    ):
        """
        Store individual step execution result.
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO step_memory (
            goal,
            step,
            result,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """, (
            goal,
            json.dumps(step),
            json.dumps(result),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    # ========================================================
    # STORE TASK SUMMARY
    # ========================================================

    def store_task_summary(
        self,
        goal: str,
        plan: dict
    ):
        """
        Store completed task summary.
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO task_memory (
            goal,
            plan,
            created_at
        )
        VALUES (?, ?, ?)
        """, (
            goal,
            json.dumps(plan),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    # ========================================================
    # RETRIEVE RECENT TASKS
    # ========================================================

    def get_recent_tasks(
        self,
        limit: int = 5
    ) -> list:
        """
        Retrieve recent completed tasks.
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        SELECT goal, plan, created_at
        FROM task_memory
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        conn.close()

        tasks = []

        for row in rows:

            tasks.append({
                "goal": row[0],
                "plan": json.loads(row[1]),
                "created_at": row[2]
            })

        return tasks

    # ========================================================
    # RETRIEVE STEP HISTORY
    # ========================================================

    def get_step_history(
        self,
        limit: int = 10
    ) -> list:
        """
        Retrieve recent step execution history.
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        SELECT goal, step, result, created_at
        FROM step_memory
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        conn.close()

        history = []

        for row in rows:

            history.append({
                "goal": row[0],
                "step": json.loads(row[1]),
                "result": json.loads(row[2]),
                "created_at": row[3]
            })

        return history
