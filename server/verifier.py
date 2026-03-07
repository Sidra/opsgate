"""
OpsGate Verifier — THE MOST IMPORTANT FILE.

Deterministic reward function modeled after RoboGraph's safety_score.py:
- Weighted multi-metric scoring (6 categories, 100 points total)
- A-F letter grades
- 3-way verdict: PASS / HOLD / BLOCK (like RoboGraph's ship/hold/investigate)
- Per-category breakdown with points/max/value

Runs in < 1ms. No LLM calls. Pure Python assertions.
"""

from hyperparameters import (
    SCORE_WEIGHTS,
    GRADE_THRESHOLDS,
    GRADE_COLORS,
    VERDICT_THRESHOLDS,
    REWARD_PASS,
    REWARD_HOLD,
    REWARD_BLOCK,
)


def _compute_grade(score: float) -> str:
    """Convert a 0-100 score to a letter grade.

    Matches RoboGraph's grading system.
    """
    if score >= GRADE_THRESHOLDS["A"]:
        return "A"
    elif score >= GRADE_THRESHOLDS["B"]:
        return "B"
    elif score >= GRADE_THRESHOLDS["C"]:
        return "C"
    elif score >= GRADE_THRESHOLDS["D"]:
        return "D"
    return "F"


def _compute_verdict(score: float, policy_violations: int, has_critical_fail: bool) -> str:
    """Decide PASS / HOLD / BLOCK based on results.

    Modeled after RoboGraph's _recommendation() logic:
    - ship  -> PASS  (score >= 90 AND zero critical failures)
    - hold  -> HOLD  (score >= 60 OR minor issues)
    - investigate -> BLOCK (score < 60 OR critical failures)
    """
    if has_critical_fail:
        return "BLOCK"
    if policy_violations > 0 and score < VERDICT_THRESHOLDS["hold_min_score"]:
        return "BLOCK"
    if policy_violations > 0:
        return "HOLD"
    if score >= VERDICT_THRESHOLDS["pass_min_score"]:
        return "PASS"
    if score >= VERDICT_THRESHOLDS["hold_min_score"]:
        return "HOLD"
    return "BLOCK"


def _verdict_to_reward(verdict: str) -> float:
    """Map verdict to RL reward signal."""
    if verdict == "PASS":
        return REWARD_PASS
    elif verdict == "HOLD":
        return REWARD_HOLD
    return REWARD_BLOCK


def verify_episode(
    target: dict,
    snapshots: dict,
    policy_violations: int = 0,
    invalid_calls: int = 0,
    tool_calls_made: int = 0,
) -> tuple[float, list[str], dict]:
    """
    Compare target state against actual DB snapshots using weighted scoring.

    Modeled after RoboGraph's _compute_score():
    Each category contributes points/max/value to a 100-point total.

    Returns:
        reward: float score for RL training
        violations: list of human-readable violation strings
        verdict: structured dict with PASS/HOLD/BLOCK decision + full breakdown
    """
    violations = []
    breakdown = {}
    score = 0.0

    # Track per-category results
    crm_checks_passed = 0
    crm_checks_total = 0
    billing_checks_passed = 0
    billing_checks_total = 0
    calendar_checks_passed = 0
    calendar_checks_total = 0
    email_checks_passed = 0
    email_checks_total = 0

    # ═══════════════════════════════════════════════════════════
    #  Run all checks (same logic as before, but now counting)
    # ═══════════════════════════════════════════════════════════

    # --- CRM checks ---
    if "crm" in target:
        crm_snap = snapshots.get("crm", {})
        for expected_user in target["crm"].get("users", []):
            crm_checks_total += 1
            uid = expected_user["user_id"]
            actual = next(
                (u for u in crm_snap.get("users", []) if u["user_id"] == uid),
                None,
            )
            if not actual:
                violations.append(f"CRM: user {uid} not found")
                continue

            match = True
            for key, val in expected_user.items():
                if key == "user_id":
                    continue
                if key == "notes_contains":
                    if val.lower() not in actual.get("notes", "").lower():
                        violations.append(f"CRM: user {uid} notes missing '{val}'")
                        match = False
                elif actual.get(key) != val:
                    violations.append(
                        f"CRM: user {uid}.{key} = {actual.get(key)!r}, expected {val!r}"
                    )
                    match = False
            if match:
                crm_checks_passed += 1

    # --- Billing checks ---
    if "billing" in target:
        bill_snap = snapshots.get("billing", {})

        for expected_inv in target["billing"].get("invoices", []):
            billing_checks_total += 1
            iid = expected_inv["invoice_id"]
            actual = next(
                (i for i in bill_snap.get("invoices", []) if i["invoice_id"] == iid),
                None,
            )
            if not actual:
                violations.append(f"Billing: invoice {iid} not found")
                continue
            match = True
            for key, val in expected_inv.items():
                if key == "invoice_id":
                    continue
                if actual.get(key) != val:
                    violations.append(
                        f"Billing: invoice {iid}.{key} = {actual.get(key)!r}, expected {val!r}"
                    )
                    match = False
            if match:
                billing_checks_passed += 1

        for expected_ref in target["billing"].get("refunds", []):
            billing_checks_total += 1
            uid = expected_ref["user_id"]
            amt = expected_ref["amount"]
            matching = [
                r for r in bill_snap.get("refunds", [])
                if r["user_id"] == uid and abs(r["amount"] - amt) < 0.01
            ]
            if matching:
                billing_checks_passed += 1
            else:
                violations.append(f"Billing: no refund for user {uid} of ${amt}")

    # --- Calendar checks ---
    if "calendar" in target:
        cal_snap = snapshots.get("calendar", {})

        for expected_evt in target["calendar"].get("events", []):
            calendar_checks_total += 1
            eid = expected_evt["event_id"]
            actual = next(
                (e for e in cal_snap.get("events", []) if e["event_id"] == eid),
                None,
            )
            if not actual:
                violations.append(f"Calendar: event {eid} not found")
                continue
            match = True
            for key, val in expected_evt.items():
                if key == "event_id":
                    continue
                if actual.get(key) != val:
                    violations.append(
                        f"Calendar: event {eid}.{key} = {actual.get(key)!r}, expected {val!r}"
                    )
                    match = False
            if match:
                calendar_checks_passed += 1

        if "events_min_count" in target["calendar"]:
            calendar_checks_total += 1
            if len(cal_snap.get("events", [])) >= target["calendar"]["events_min_count"]:
                calendar_checks_passed += 1
            else:
                violations.append("Calendar: not enough events created")

    # --- Email checks ---
    if "email" in target:
        email_snap = snapshots.get("email", {})
        outbox = email_snap.get("outbox", [])

        for expected_email in target["email"].get("outbox_contains", []):
            email_checks_total += 1
            matching = [e for e in outbox if e["to"] == expected_email["to"]]
            if matching:
                email_checks_passed += 1
            else:
                violations.append(f"Email: no email sent to {expected_email['to']}")

        if "outbox_min_count" in target["email"]:
            email_checks_total += 1
            if len(outbox) >= target["email"]["outbox_min_count"]:
                email_checks_passed += 1
            else:
                violations.append(
                    f"Email: sent {len(outbox)}, need {target['email']['outbox_min_count']}"
                )

    # ═══════════════════════════════════════════════════════════
    #  Weighted Scoring (modeled after RoboGraph safety_score.py)
    # ═══════════════════════════════════════════════════════════

    total_checks = crm_checks_total + billing_checks_total + calendar_checks_total + email_checks_total
    total_passed = crm_checks_passed + billing_checks_passed + calendar_checks_passed + email_checks_passed

    if total_checks == 0:
        verdict = {
            "decision": "BLOCK",
            "reason": "No checks defined",
            "score": 0.0,
            "grade": "F",
            "color": GRADE_COLORS["F"],
            "breakdown": {},
            "violations": ["No checks defined"],
            "policy_violations_count": policy_violations,
            "reward": REWARD_BLOCK,
        }
        return REWARD_BLOCK, ["No checks defined"], verdict

    completion_ratio = total_passed / total_checks

    # 1. Task Completion (30 pts)
    w = SCORE_WEIGHTS["task_completion"]
    tc_pts = round(completion_ratio * w["max_points"], 1)
    score += tc_pts
    breakdown["task_completion"] = {
        "points": tc_pts,
        "max": w["max_points"],
        "value": f"{total_passed}/{total_checks}",
        "description": w["description"],
    }

    # 2. Policy Compliance (20 pts)
    w = SCORE_WEIGHTS["policy_compliance"]
    pc_pts = round(max(0, w["max_points"] - policy_violations * w["penalty_per_violation"]), 1)
    score += pc_pts
    breakdown["policy_compliance"] = {
        "points": pc_pts,
        "max": w["max_points"],
        "value": policy_violations,
        "description": w["description"],
    }

    # 3. Tool Efficiency (15 pts)
    w = SCORE_WEIGHTS["tool_efficiency"]
    extra_calls = max(0, tool_calls_made - w["optimal_calls"])
    te_pts = round(max(0, w["max_points"] - extra_calls * w["penalty_per_extra"]), 1)
    score += te_pts
    breakdown["tool_efficiency"] = {
        "points": te_pts,
        "max": w["max_points"],
        "value": tool_calls_made,
        "description": w["description"],
    }

    # 4. Notification Completeness (15 pts)
    w = SCORE_WEIGHTS["notification_completeness"]
    if email_checks_total > 0:
        nc_ratio = email_checks_passed / email_checks_total
    else:
        nc_ratio = 1.0  # no email checks = assume ok
    nc_pts = round(nc_ratio * w["max_points"], 1)
    score += nc_pts
    breakdown["notification_completeness"] = {
        "points": nc_pts,
        "max": w["max_points"],
        "value": f"{email_checks_passed}/{email_checks_total}",
        "description": w["description"],
    }

    # 5. State Accuracy (10 pts)
    w = SCORE_WEIGHTS["state_accuracy"]
    non_email_total = crm_checks_total + billing_checks_total + calendar_checks_total
    non_email_passed = crm_checks_passed + billing_checks_passed + calendar_checks_passed
    if non_email_total > 0:
        sa_ratio = non_email_passed / non_email_total
    else:
        sa_ratio = 1.0
    sa_pts = round(sa_ratio * w["max_points"], 1)
    score += sa_pts
    breakdown["state_accuracy"] = {
        "points": sa_pts,
        "max": w["max_points"],
        "value": f"{non_email_passed}/{non_email_total}",
        "description": w["description"],
    }

    # 6. Action Hygiene (10 pts)
    w = SCORE_WEIGHTS["action_hygiene"]
    ah_pts = round(max(0, w["max_points"] - invalid_calls * w["penalty_per_invalid"]), 1)
    score += ah_pts
    breakdown["action_hygiene"] = {
        "points": ah_pts,
        "max": w["max_points"],
        "value": invalid_calls,
        "description": w["description"],
    }

    # ═══════════════════════════════════════════════════════════
    #  Grade + Verdict + Reward
    # ═══════════════════════════════════════════════════════════

    score = round(min(100, max(0, score)), 1)
    grade = _compute_grade(score)
    has_critical_fail = completion_ratio < 0.5
    decision = _compute_verdict(score, policy_violations, has_critical_fail)
    reward = _verdict_to_reward(decision)

    verdict = {
        "decision": decision,
        "score": score,
        "grade": grade,
        "color": GRADE_COLORS[grade],
        "breakdown": breakdown,
        "violations": violations,
        "checks_passed": total_passed,
        "checks_total": total_checks,
        "policy_violations_count": policy_violations,
        "invalid_calls": invalid_calls,
        "tool_calls_made": tool_calls_made,
        "reward": round(reward, 4),
    }

    return reward, violations, verdict
