"""OpsGate data models — Pydantic v2 for OpenEnv compatibility."""
from pydantic import BaseModel, Field
from typing import Optional


class ToolCall(BaseModel):
    tool: str = ""
    action: str = ""
    parameters: dict = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool = False
    data: dict = Field(default_factory=dict)
    error: Optional[str] = None
    reward: float = 0.0
    done: bool = False
    step_count: int = 0
    task_description: str = ""
    tools_available: list = Field(default_factory=lambda: ["crm", "billing", "calendar", "email"])


class AuditEvent(BaseModel):
    event_type: str = ""
    action: str = ""
    title: str = ""
    detail: str = ""
    severity: str = "info"
    step: int = 0


class EpisodeState(BaseModel):
    task_id: str = ""
    task_description: str = ""
    target_state: dict = Field(default_factory=dict)
    current_db_snapshot: dict = Field(default_factory=dict)
    tool_calls_made: int = 0
    invalid_calls: int = 0
    policy_violations: int = 0
    completed: bool = False
    verdict: dict = Field(default_factory=dict)
    audit_trail: list = Field(default_factory=list)
