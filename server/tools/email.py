"""Email Tool — in-memory outbox queue.

Supports: send, list_sent.
Used by OpsGate environment to simulate enterprise email operations.
"""


class EmailTool:
    """In-memory email outbox simulator."""

    def __init__(self):
        self.outbox: list[dict] = []

    def execute(self, action: str, params: dict) -> dict:
        """Route and execute an email action."""
        if action == "send":
            if not params.get("to") or not params.get("subject") or not params.get("body"):
                return {"error": "Email requires 'to', 'subject', and 'body' parameters"}
            msg = {
                "to": params["to"],
                "subject": params["subject"],
                "body": params["body"],
            }
            self.outbox.append(msg)
            return {"success": True, "message_id": len(self.outbox)}
        elif action == "list_sent":
            return {"emails": self.outbox}
        return {"error": f"Unknown email action: {action}"}

    def snapshot(self) -> dict:
        """Return complete email state for verification."""
        return {"outbox": self.outbox}

    def reset(self):
        """Clear the outbox."""
        self.outbox = []
