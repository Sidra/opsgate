"""Calendar Tool — in-memory SQLite event management.

Supports: list_events, create_event, cancel_event, reschedule_event.
Used by OpsGate environment to simulate enterprise calendar operations.
"""

import sqlite3


class CalendarTool:
    """SQLite-backed calendar simulator.

    Params
    ======
        db_path (str): SQLite database path (":memory:" for in-memory)
    """

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Create calendar tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                attendees TEXT,
                datetime TEXT,
                duration_min INTEGER DEFAULT 30,
                status TEXT DEFAULT 'scheduled',
                notes TEXT DEFAULT ''
            );
        """)
        self.conn.commit()

    def seed(self, events: list[dict]):
        """Seed calendar with initial event data."""
        for e in events:
            self.conn.execute(
                "INSERT INTO events "
                "(title, attendees, datetime, duration_min, status, notes) "
                "VALUES (:title, :attendees, :datetime, :duration_min, :status, :notes)", e
            )
        self.conn.commit()

    def execute(self, action: str, params: dict) -> dict:
        """Route and execute a calendar action."""
        actions = {
            "list_events": self._list_events,
            "create_event": self._create_event,
            "cancel_event": self._cancel_event,
            "reschedule_event": self._reschedule_event,
        }
        if action not in actions:
            return {"error": f"Unknown calendar action: {action}"}
        try:
            return actions[action](params)
        except Exception as e:
            return {"error": str(e)}

    def _list_events(self, params):
        if "attendee" in params:
            rows = self.conn.execute(
                "SELECT * FROM events WHERE attendees LIKE ?",
                (f"%{params['attendee']}%",)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM events").fetchall()
        return {"events": [dict(r) for r in rows]}

    def _create_event(self, params):
        cur = self.conn.execute(
            "INSERT INTO events (title, attendees, datetime, duration_min, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (params["title"], params.get("attendees", ""),
             params["datetime"], params.get("duration_min", 30),
             params.get("notes", ""))
        )
        self.conn.commit()
        return {"success": True, "event_id": cur.lastrowid}

    def _cancel_event(self, params):
        self.conn.execute(
            "UPDATE events SET status = 'cancelled' WHERE event_id = ?",
            (params["event_id"],)
        )
        self.conn.commit()
        return {"success": True}

    def _reschedule_event(self, params):
        self.conn.execute(
            "UPDATE events SET datetime = ?, status = 'rescheduled' WHERE event_id = ?",
            (params["new_datetime"], params["event_id"])
        )
        self.conn.commit()
        return {"success": True}

    def snapshot(self) -> dict:
        """Return complete calendar state for verification."""
        events = self.conn.execute("SELECT * FROM events").fetchall()
        return {"events": [dict(r) for r in events]}
