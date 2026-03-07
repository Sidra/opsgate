"""OpsGate Environment — the core reset/step/state loop."""
import uuid
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openenv.core.env_server.interfaces import Environment
from models import ToolCall, ToolResult, EpisodeState, AuditEvent
from server.tools.crm import CRMTool
from server.tools.billing import BillingTool
from server.tools.calendar import CalendarTool
from server.tools.email import EmailTool
from server.verifier import verify_episode
from tasks import TASKS
from hyperparameters import (
    MAX_STEPS_PER_EPISODE, TOOL_CALL_PENALTY, INVALID_TOOL_PENALTY,
)


class OpsGateEnvironment(Environment):

    def __init__(self):
        super().__init__()
        self.crm = CRMTool()
        self.billing = BillingTool()
        self.calendar = CalendarTool()
        self.email = EmailTool()
        self._state = None
        self._current_task = None
        self._task_index = 0

    def _log_audit(self, event_type, action, title, detail="", severity="info"):
        if self._state and self._state.audit_trail is not None:
            event = AuditEvent(
                event_type=event_type, action=action, title=title,
                detail=detail, severity=severity,
                step=self._state.tool_calls_made if self._state else 0,
            )
            self._state.audit_trail.append(event.__dict__)

    def reset(self):
        task = TASKS[self._task_index % len(TASKS)]
        self._task_index += 1
        self._current_task = task

        self.crm = CRMTool()
        self.billing = BillingTool()
        self.calendar = CalendarTool()
        self.email = EmailTool()

        seed = task["seed"]
        if seed.get("users"):
            self.crm.seed(seed["users"])
        if seed.get("invoices"):
            self.billing.seed(seed["invoices"])
        if seed.get("events"):
            self.calendar.seed(seed["events"])

        self._state = EpisodeState(
            task_id=task["id"],
            task_description=task["description"],
            target_state=task["target"],
            current_db_snapshot={},
            tool_calls_made=0,
            invalid_calls=0,
            policy_violations=0,
            completed=False,
            verdict={},
            audit_trail=[],
        )

        self._log_audit("episode", "started", f"Episode started: {task['id']}", task["description"][:100])

        return ToolResult(
            success=True,
            data={"message": "Environment ready. Complete the following task."},
            task_description=task["description"],
            step_count=0,
            done=False,
        )

    def step(self, action):
        if self._state is None:
            return ToolResult(success=False, error="Call reset() first", reward=-1.0, done=True)

        self._state.tool_calls_made += 1

        tool_map = {"crm": self.crm, "billing": self.billing, "calendar": self.calendar, "email": self.email}

        tool_name = action.tool if hasattr(action, 'tool') else action.get('tool', '')
        action_name = action.action if hasattr(action, 'action') else action.get('action', '')
        params = action.parameters if hasattr(action, 'parameters') else action.get('parameters', {})

        tool = tool_map.get(tool_name)
        if not tool:
            self._state.invalid_calls += 1
            self._log_audit("tool_call", "invalid_tool", f"Unknown tool: {tool_name}", severity="warning")
            return ToolResult(
                success=False, error=f"Unknown tool: {tool_name}",
                reward=INVALID_TOOL_PENALTY, done=False,
                step_count=self._state.tool_calls_made,
                task_description=self._current_task["description"],
            )

        self._log_audit("tool_call", f"{tool_name}.{action_name}", f"Tool call: {tool_name}.{action_name}", str(params)[:200])

        result = tool.execute(action_name, params)

        if "error" in result:
            sev = "critical" if result.get("policy_violated") else "warning"
            self._log_audit("tool_result", "error", f"Tool error: {tool_name}.{action_name}", result["error"][:200], sev)
            if result.get("policy_violated"):
                self._state.policy_violations += 1
        else:
            self._log_audit("tool_result", "success", f"Tool success: {tool_name}.{action_name}", str(result)[:200], "success")

        reward = TOOL_CALL_PENALTY
        max_steps = self._current_task.get("max_steps", MAX_STEPS_PER_EPISODE)
        done = (action_name == "submit") or (self._state.tool_calls_made >= max_steps)

        if done:
            snapshots = {
                "crm": self.crm.snapshot(), "billing": self.billing.snapshot(),
                "calendar": self.calendar.snapshot(), "email": self.email.snapshot(),
            }
            reward, violations, verdict = verify_episode(
                target=self._current_task["target"], snapshots=snapshots,
                policy_violations=self._state.policy_violations,
                invalid_calls=self._state.invalid_calls,
                tool_calls_made=self._state.tool_calls_made,
            )
            self._state.completed = True
            self._state.current_db_snapshot = snapshots
            self._state.verdict = verdict
            self._log_audit("verdict", verdict["decision"],
                f"Safety gate {verdict['decision']}: {self._current_task['id']}",
                f"Score: {verdict['score']}/100 (Grade {verdict['grade']})",
                "success" if verdict["decision"] == "PASS" else "warning" if verdict["decision"] == "HOLD" else "critical")
            result["_verification"] = verdict

        return ToolResult(
            success="error" not in result, data=result, reward=reward, done=done,
            step_count=self._state.tool_calls_made,
            task_description=self._current_task["description"],
        )

    @property
    def state(self):
        return self._state
