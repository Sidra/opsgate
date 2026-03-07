"""Billing Tool — in-memory SQLite invoices, refunds, and subscriptions.

Enforces business policy: refunds > $500 require manager approval.
Used by OpsGate environment to simulate enterprise billing operations.
"""

import sqlite3


class BillingTool:
    """SQLite-backed billing simulator with policy enforcement.

    Params
    ======
        db_path (str): SQLite database path (":memory:" for in-memory)
    """

    # Business policy constants (agent must learn these)
    MAX_REFUND_WITHOUT_APPROVAL = 500.00
    PRORATE_POLICY = True

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Create billing tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'paid',
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS refunds (
                refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                user_id INTEGER,
                amount REAL,
                reason TEXT,
                status TEXT DEFAULT 'processed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def seed(self, invoices: list[dict]):
        """Seed billing with initial invoice data."""
        for inv in invoices:
            self.conn.execute(
                "INSERT OR REPLACE INTO invoices "
                "(invoice_id, user_id, amount, status, description) "
                "VALUES (:invoice_id, :user_id, :amount, :status, :description)", inv
            )
        self.conn.commit()

    def execute(self, action: str, params: dict) -> dict:
        """Route and execute a billing action."""
        actions = {
            "get_invoice": self._get_invoice,
            "list_invoices": self._list_invoices,
            "issue_refund": self._issue_refund,
            "cancel_subscription": self._cancel_subscription,
        }
        if action not in actions:
            return {"error": f"Unknown billing action: {action}"}
        try:
            return actions[action](params)
        except Exception as e:
            return {"error": str(e)}

    def _get_invoice(self, params):
        row = self.conn.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?", (params["invoice_id"],)
        ).fetchone()
        return dict(row) if row else {"error": "Invoice not found"}

    def _list_invoices(self, params):
        rows = self.conn.execute(
            "SELECT * FROM invoices WHERE user_id = ?", (params["user_id"],)
        ).fetchall()
        return {"invoices": [dict(r) for r in rows]}

    def _issue_refund(self, params):
        amount = params["amount"]
        # POLICY CHECK: refunds > $500 require approval
        if amount > self.MAX_REFUND_WITHOUT_APPROVAL:
            return {
                "error": "POLICY_VIOLATION: Refunds > $500 require manager approval",
                "policy_violated": True,
            }
        self.conn.execute(
            "INSERT INTO refunds (invoice_id, user_id, amount, reason) "
            "VALUES (?, ?, ?, ?)",
            (params["invoice_id"], params["user_id"], amount,
             params.get("reason", ""))
        )
        self.conn.execute(
            "UPDATE invoices SET status = 'refunded' WHERE invoice_id = ?",
            (params["invoice_id"],)
        )
        self.conn.commit()
        return {"success": True, "refund_amount": amount}

    def _cancel_subscription(self, params):
        self.conn.execute(
            "UPDATE invoices SET status = 'cancelled' WHERE user_id = ? AND status = 'paid'",
            (params["user_id"],)
        )
        self.conn.commit()
        return {"success": True}

    def snapshot(self) -> dict:
        """Return complete billing state for verification."""
        invoices = self.conn.execute("SELECT * FROM invoices").fetchall()
        refunds = self.conn.execute("SELECT * FROM refunds").fetchall()
        return {
            "invoices": [dict(r) for r in invoices],
            "refunds": [dict(r) for r in refunds],
        }
