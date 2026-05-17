import sqlite3
from contextlib import contextmanager

from config.config import MEMORY_CONFIG


class SQLiteDB:
    """
    Lightweight SQLite database wrapper for NextMind.

    Responsibilities:
    - Manage database connections
    - Provide reusable query helpers
    - Centralize SQLite operations
    """

    def __init__(self):

        self.db_path = MEMORY_CONFIG.SQLITE_DB_PATH

    # ========================================================
    # CONNECTION MANAGER
    # ========================================================

    @contextmanager
    def connect(self):
        """
        Context-managed SQLite connection.

        Automatically commits changes and closes
        connection safely.
        """

        conn = sqlite3.connect(self.db_path)

        try:
            yield conn
            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    # ========================================================
    # EXECUTE WRITE QUERY
    # ========================================================

    def execute(
        self,
        query: str,
        params: tuple = ()
    ):
        """
        Execute INSERT/UPDATE/DELETE queries.
        """

        with self.connect() as conn:

            cursor = conn.cursor()

            cursor.execute(query, params)

    # ========================================================
    # FETCH ONE
    # ========================================================

    def fetch_one(
        self,
        query: str,
        params: tuple = ()
    ):
        """
        Fetch a single database row.
        """

        with self.connect() as conn:

            cursor = conn.cursor()

            cursor.execute(query, params)

            return cursor.fetchone()

    # ========================================================
    # FETCH ALL
    # ========================================================

    def fetch_all(
        self,
        query: str,
        params: tuple = ()
    ):
        """
        Fetch multiple database rows.
        """

        with self.connect() as conn:

            cursor = conn.cursor()

            cursor.execute(query, params)

            return cursor.fetchall()
