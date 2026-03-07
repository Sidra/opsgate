"""CRM Tool — in-memory SQLite customer relationship management.

Supports: get_user, update_user, add_note, log_interaction, list_users.
Used by OpsGate environment to simulate enterprise CRM operations.
"""

import sqlite3


class CRMTool:
    """SQLite-backed CRM simulator.

    Params
    ======
        db_path (str): SQLite database path (":memory:" for in-memory)
    """

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Create CRM tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                plan TEXT DEFAULT 'basic',
                status TEXT DEFAULT 'active',
                account_manager TEXT,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(user_id),
                type TEXT,
                summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def seed(self, users: list[dict]):
        """Seed CRM with initial user data."""
        for u in users:
            self.conn.execute(
                "INSERT OR REPLACE INTO users "
                "(user_id, name, email, plan, status, account_manager, notes) "
                "VALUES (:user_id, :name, :email, :plan, :status, :account_manager, :notes)", u
            )
        self.conn.commit()

    def execute(self, action: str, params: dict) -> dict:
        """Route and execute a CRM action."""
        actions = {
            "get_user": self._get_user,
            "update_user": self._update_user,
            "add_note": self._add_note,
            "log_interaction": self._log_interaction,
            "list_users": self._list_users,
        }
        if action not in actions:
            return {"error": f"Unknown CRM action: {action}"}
        try:
            return actions[action](params)
        except Exception as e:
            return {"error": str(e)}

    def _get_user(self, params):
        row = self.conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (params["user_id"],)
        ).fetchone()
        return dict(row) if row else {"error": "User not found"}

    def _update_user(self, params):
        user_id = params.pop("user_id")
        sets = ", ".join(f"{k} = ?" for k in params)
        vals = list(params.values()) + [user_id]
        self.conn.execute(f"UPDATE users SET {sets} WHERE user_id = ?", vals)
        self.conn.commit()
        return {"success": True, "updated_fields": list(params.keys())}

    def _add_note(self, params):
        self.conn.execute(
            "UPDATE users SET notes = notes || ? || char(10) WHERE user_id = ?",
            (params["note"], params["user_id"])
        )
        self.conn.commit()
        return {"success": True}

    def _log_interaction(self, params):
        self.conn.execute(
            "INSERT INTO interactions (user_id, type, summary) VALUES (?, ?, ?)",
            (params["user_id"], params["type"], params["summary"])
        )
        self.conn.commit()
        return {"success": True}

    def _list_users(self, params):
        rows = self.conn.execute("SELECT * FROM users").fetchall()
        return {"users": [dict(r) for r in rows]}

    def snapshot(self) -> dict:
        """Return complete CRM state for verification."""
        users = self.conn.execute("SELECT * FROM users").fetchall()
        interactions = self.conn.execute("SELECT * FROM interactions").fetchall()
        return {
            "users": [dict(r) for r in users],
            "interactions": [dict(r) for r in interactions],
        }
