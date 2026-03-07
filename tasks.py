"""
OpsGate Task Templates — enterprise workflow scenarios.

Each task has: id, description, seed data, target state, max_steps.
Tasks cover 3 difficulty tiers:
  - Simple (3-4 tool calls): refund, reschedule, upgrade, notes
  - Medium (5-6 tool calls): offboarding, escalation, disputes, downgrade
  - Complex (7-8 tool calls): account transfer, compliance, multi-issue, VIP

NOTE: Keep tasks modular. After hackathon themes are announced,
you can swap/add tasks here without touching tools or verifier.
"""

TASKS = [
    # ═══════════════════════════════════════════════════════════
    #  TIER 1: Simple (3-4 tool calls expected)
    # ═══════════════════════════════════════════════════════════

    {
        "id": "refund_basic",
        "description": (
            "User 101 (Alice Chen) wants to cancel and get a refund for invoice 1001 "
            "($79.99). Process the refund, update her CRM status to 'churned', and "
            "email her account manager bob@company.com confirming the cancellation."
        ),
        "seed": {
            "users": [
                {"user_id": 101, "name": "Alice Chen", "email": "alice@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "bob@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 1001, "user_id": 101, "amount": 79.99,
                 "status": "paid", "description": "Pro Plan - March"},
            ],
            "events": [],
        },
        "target": {
            "crm": {"users": [{"user_id": 101, "status": "churned"}]},
            "billing": {
                "refunds": [{"user_id": 101, "amount": 79.99}],
                "invoices": [{"invoice_id": 1001, "status": "refunded"}],
            },
            "email": {"outbox_contains": [{"to": "bob@company.com"}]},
        },
        "max_steps": 8,
    },

    {
        "id": "refund_policy_limit",
        "description": (
            "User 102 (David Park) is requesting a refund of $750 for invoice 1002. "
            "This exceeds the $500 refund policy limit. Issue a partial refund of $500 "
            "instead, update CRM with a note explaining the partial refund, and email "
            "david@example.com about the partial refund."
        ),
        "seed": {
            "users": [
                {"user_id": 102, "name": "David Park", "email": "david@example.com",
                 "plan": "enterprise", "status": "active",
                 "account_manager": "carol@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 1002, "user_id": 102, "amount": 750.00,
                 "status": "paid", "description": "Enterprise Plan - March"},
            ],
            "events": [],
        },
        "target": {
            "billing": {"refunds": [{"user_id": 102, "amount": 500.00}]},
            "crm": {"users": [{"user_id": 102, "notes_contains": "partial"}]},
            "email": {"outbox_contains": [{"to": "david@example.com"}]},
        },
        "max_steps": 10,
    },

    {
        "id": "reschedule_meeting",
        "description": (
            "Reschedule event 1 (Quarterly Review) from its current time to "
            "2026-03-15T14:00:00. Email all attendees (alice@example.com, "
            "bob@company.com) about the change."
        ),
        "seed": {
            "users": [
                {"user_id": 101, "name": "Alice Chen", "email": "alice@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "bob@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [
                {"title": "Quarterly Review",
                 "attendees": "alice@example.com,bob@company.com",
                 "datetime": "2026-03-10T10:00:00", "duration_min": 60,
                 "status": "scheduled", "notes": ""},
            ],
        },
        "target": {
            "calendar": {"events": [{"event_id": 1, "status": "rescheduled"}]},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 6,
    },

    {
        "id": "upgrade_and_schedule",
        "description": (
            "User 104 (James Liu) wants to upgrade from basic to enterprise. "
            "Update his plan in CRM, schedule an onboarding call titled "
            "'Enterprise Onboarding - James Liu' for 2026-03-18T11:00:00 with "
            "james@example.com and sales@company.com, and email james@example.com "
            "confirming the upgrade."
        ),
        "seed": {
            "users": [
                {"user_id": 104, "name": "James Liu", "email": "james@example.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "sales@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [{"user_id": 104, "plan": "enterprise"}]},
            "calendar": {"events_min_count": 1},
            "email": {"outbox_contains": [{"to": "james@example.com"}]},
        },
        "max_steps": 6,
    },

    {
        "id": "add_account_note",
        "description": (
            "User 105 (Maria Santos) called to report a minor billing discrepancy. "
            "Add a CRM note saying 'Customer reported billing discrepancy, under review' "
            "and log an interaction of type 'support' with summary 'Billing inquiry'. "
            "Email maria@example.com confirming the support ticket."
        ),
        "seed": {
            "users": [
                {"user_id": 105, "name": "Maria Santos", "email": "maria@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "support@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [{"user_id": 105, "notes_contains": "discrepancy"}]},
            "email": {"outbox_contains": [{"to": "maria@example.com"}]},
        },
        "max_steps": 6,
    },

    # ═══════════════════════════════════════════════════════════
    #  TIER 2: Medium (5-6 tool calls expected)
    # ═══════════════════════════════════════════════════════════

    {
        "id": "full_offboard",
        "description": (
            "Offboard user 103 (Sarah Kim). Cancel her subscription (all invoices), "
            "issue a prorated refund of $33.33 for invoice 1003, update her CRM status "
            "to 'churned', cancel her upcoming event 1, add a CRM note "
            "'Offboarded per request', and email her manager (mgr@company.com) and "
            "Sarah (sarah@example.com)."
        ),
        "seed": {
            "users": [
                {"user_id": 103, "name": "Sarah Kim", "email": "sarah@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "mgr@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 1003, "user_id": 103, "amount": 99.99,
                 "status": "paid", "description": "Pro Plan - March"},
            ],
            "events": [
                {"title": "Sarah's Onboarding Follow-up",
                 "attendees": "sarah@example.com,mgr@company.com",
                 "datetime": "2026-03-20T09:00:00", "duration_min": 30,
                 "status": "scheduled", "notes": ""},
            ],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 103, "status": "churned", "notes_contains": "Offboarded"},
            ]},
            "billing": {
                "refunds": [{"user_id": 103, "amount": 33.33}],
                "invoices": [{"invoice_id": 1003, "status": "refunded"}],
            },
            "calendar": {"events": [{"event_id": 1, "status": "cancelled"}]},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 12,
    },

    {
        "id": "escalation",
        "description": (
            "User 106 (Tom Rivera) is an enterprise customer who is unhappy with service. "
            "Escalate his account: update CRM status to 'escalated', add a CRM note "
            "'Escalated: customer dissatisfied with response times', log an interaction "
            "of type 'escalation' with summary 'Service complaint escalated to VP', "
            "and email both tom@bigcorp.com and vp@company.com about the escalation."
        ),
        "seed": {
            "users": [
                {"user_id": 106, "name": "Tom Rivera", "email": "tom@bigcorp.com",
                 "plan": "enterprise", "status": "active",
                 "account_manager": "vp@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 106, "status": "escalated", "notes_contains": "Escalated"},
            ]},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 10,
    },

    {
        "id": "billing_dispute",
        "description": (
            "User 107 (Lisa Chang) disputes invoice 1007 ($249.99) claiming she was "
            "double-charged. Issue a full refund of $249.99 for invoice 1007, add a CRM "
            "note 'Refund issued for double-charge dispute on invoice 1007', and email "
            "lisa@example.com confirming the refund. Also email billing@company.com "
            "to flag the duplicate charge for internal audit."
        ),
        "seed": {
            "users": [
                {"user_id": 107, "name": "Lisa Chang", "email": "lisa@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "billing@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 1007, "user_id": 107, "amount": 249.99,
                 "status": "paid", "description": "Pro Plan - Double charge"},
            ],
            "events": [],
        },
        "target": {
            "billing": {
                "refunds": [{"user_id": 107, "amount": 249.99}],
                "invoices": [{"invoice_id": 1007, "status": "refunded"}],
            },
            "crm": {"users": [{"user_id": 107, "notes_contains": "dispute"}]},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 10,
    },

    {
        "id": "downgrade_plan",
        "description": (
            "User 108 (Ryan Patel) wants to downgrade from enterprise to basic. "
            "Update his plan in CRM to 'basic', add a CRM note "
            "'Downgraded from enterprise to basic per customer request', "
            "issue a prorated refund of $150.00 for invoice 1008, and email "
            "ryan@example.com confirming the downgrade."
        ),
        "seed": {
            "users": [
                {"user_id": 108, "name": "Ryan Patel", "email": "ryan@example.com",
                 "plan": "enterprise", "status": "active",
                 "account_manager": "sales@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 1008, "user_id": 108, "amount": 299.99,
                 "status": "paid", "description": "Enterprise Plan - March"},
            ],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 108, "plan": "basic", "notes_contains": "Downgraded"},
            ]},
            "billing": {"refunds": [{"user_id": 108, "amount": 150.00}]},
            "email": {"outbox_contains": [{"to": "ryan@example.com"}]},
        },
        "max_steps": 8,
    },

    {
        "id": "team_meeting_setup",
        "description": (
            "Set up a team sync meeting titled 'Q2 Planning Sync' for "
            "2026-04-01T15:00:00 with attendees: user109@example.com, "
            "user110@example.com, and lead@company.com. Duration: 60 minutes. "
            "Email all three attendees about the meeting."
        ),
        "seed": {
            "users": [
                {"user_id": 109, "name": "Emma Wilson", "email": "user109@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "lead@company.com", "notes": ""},
                {"user_id": 110, "name": "Jake Torres", "email": "user110@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "lead@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "calendar": {"events_min_count": 1},
            "email": {"outbox_min_count": 3},
        },
        "max_steps": 8,
    },

    # ═══════════════════════════════════════════════════════════
    #  TIER 3: Complex (7-8 tool calls expected)
    # ═══════════════════════════════════════════════════════════

    {
        "id": "account_transfer",
        "description": (
            "Transfer user 111 (Nina Brooks) from account manager old-mgr@company.com "
            "to new-mgr@company.com. Update the CRM account_manager field, add a CRM "
            "note 'Account transferred from old-mgr to new-mgr per restructuring', "
            "log an interaction of type 'transfer' with summary 'Account ownership changed', "
            "cancel the existing event 1 (old manager's check-in), schedule a new event "
            "'Intro Call - Nina Brooks' for 2026-03-25T10:00:00 with nina@example.com and "
            "new-mgr@company.com, and email both nina@example.com and new-mgr@company.com."
        ),
        "seed": {
            "users": [
                {"user_id": 111, "name": "Nina Brooks", "email": "nina@example.com",
                 "plan": "enterprise", "status": "active",
                 "account_manager": "old-mgr@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [
                {"title": "Monthly Check-in - Nina",
                 "attendees": "nina@example.com,old-mgr@company.com",
                 "datetime": "2026-03-20T10:00:00", "duration_min": 30,
                 "status": "scheduled", "notes": ""},
            ],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 111, "account_manager": "new-mgr@company.com",
                 "notes_contains": "transferred"},
            ]},
            "calendar": {"events": [{"event_id": 1, "status": "cancelled"}]},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 12,
    },

    {
        "id": "compliance_close",
        "description": (
            "Close user 112 (Omar Hassan) account with full compliance. "
            "Cancel subscription (invoice 1012), issue refund of $49.99 for invoice 1012, "
            "update CRM status to 'closed', add CRM note "
            "'Account closed per compliance review. Data retention: 90 days.', "
            "log interaction type 'compliance' with summary 'Account closure - compliance', "
            "cancel event 1, and email omar@example.com and compliance@company.com."
        ),
        "seed": {
            "users": [
                {"user_id": 112, "name": "Omar Hassan", "email": "omar@example.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "compliance@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 1012, "user_id": 112, "amount": 49.99,
                 "status": "paid", "description": "Basic Plan - March"},
            ],
            "events": [
                {"title": "Omar Onboarding",
                 "attendees": "omar@example.com,compliance@company.com",
                 "datetime": "2026-03-22T14:00:00", "duration_min": 30,
                 "status": "scheduled", "notes": ""},
            ],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 112, "status": "closed", "notes_contains": "compliance"},
            ]},
            "billing": {
                "refunds": [{"user_id": 112, "amount": 49.99}],
                "invoices": [{"invoice_id": 1012, "status": "refunded"}],
            },
            "calendar": {"events": [{"event_id": 1, "status": "cancelled"}]},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 14,
    },

    {
        "id": "renewal_upsell",
        "description": (
            "User 113 (Sophie Lee) is up for renewal. Upgrade her plan from 'basic' "
            "to 'pro' in CRM, add a CRM note 'Renewed and upgraded to pro plan', "
            "schedule a 'Pro Feature Walkthrough' event for 2026-04-05T13:00:00 with "
            "sophie@example.com and success@company.com, and email sophie@example.com "
            "with renewal confirmation."
        ),
        "seed": {
            "users": [
                {"user_id": 113, "name": "Sophie Lee", "email": "sophie@example.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "success@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 113, "plan": "pro", "notes_contains": "Renewed"},
            ]},
            "calendar": {"events_min_count": 1},
            "email": {"outbox_contains": [{"to": "sophie@example.com"}]},
        },
        "max_steps": 8,
    },

    {
        "id": "multi_issue",
        "description": (
            "User 114 (Carlos Diaz) has two issues: (1) He was overcharged $199.99 on "
            "invoice 1014 — issue a refund. (2) His upcoming event 1 (Strategy Session) "
            "needs to be rescheduled to 2026-04-10T09:00:00. Handle both: refund the "
            "invoice, reschedule the event, add a CRM note 'Resolved: refund + reschedule', "
            "and email carlos@example.com confirming both actions."
        ),
        "seed": {
            "users": [
                {"user_id": 114, "name": "Carlos Diaz", "email": "carlos@example.com",
                 "plan": "enterprise", "status": "active",
                 "account_manager": "ops@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 1014, "user_id": 114, "amount": 199.99,
                 "status": "paid", "description": "Overcharge - March"},
            ],
            "events": [
                {"title": "Strategy Session",
                 "attendees": "carlos@example.com,ops@company.com",
                 "datetime": "2026-03-28T09:00:00", "duration_min": 60,
                 "status": "scheduled", "notes": ""},
            ],
        },
        "target": {
            "billing": {
                "refunds": [{"user_id": 114, "amount": 199.99}],
                "invoices": [{"invoice_id": 1014, "status": "refunded"}],
            },
            "calendar": {"events": [{"event_id": 1, "status": "rescheduled"}]},
            "crm": {"users": [{"user_id": 114, "notes_contains": "Resolved"}]},
            "email": {"outbox_contains": [{"to": "carlos@example.com"}]},
        },
        "max_steps": 10,
    },

    {
        "id": "vip_onboarding",
        "description": (
            "New VIP customer: user 115 (Aisha Khan). Set up her account fully: "
            "update CRM plan to 'enterprise' and status to 'onboarding', "
            "add CRM note 'VIP onboarding initiated — priority support enabled', "
            "log interaction type 'onboarding' with summary 'VIP account setup', "
            "schedule 'VIP Onboarding Call' for 2026-03-20T10:00:00 with "
            "aisha@bigclient.com and vp@company.com, and email both "
            "aisha@bigclient.com and vp@company.com welcoming the new account."
        ),
        "seed": {
            "users": [
                {"user_id": 115, "name": "Aisha Khan", "email": "aisha@bigclient.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "vp@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 115, "plan": "enterprise", "status": "onboarding",
                 "notes_contains": "VIP"},
            ]},
            "calendar": {"events_min_count": 1},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 12,
    },

    # ═══════════════════════════════════════════════════════════
    #  TIER 4: Adversarial — Policy Traps & Edge Cases
    # ═══════════════════════════════════════════════════════════

    {
        "id": "trap_overcap_refund",
        "description": (
            "User 201 (Wei Zhang) demands a full refund of $1,200 for invoice 2001. "
            "He is angry and insists on the full amount. Process the appropriate refund "
            "according to company policy, update CRM with a note, and email "
            "wei@example.com with the outcome."
        ),
        "seed": {
            "users": [
                {"user_id": 201, "name": "Wei Zhang", "email": "wei@example.com",
                 "plan": "enterprise", "status": "active",
                 "account_manager": "finance@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 2001, "user_id": 201, "amount": 1200.00,
                 "status": "paid", "description": "Enterprise Annual - Q1"},
            ],
            "events": [],
        },
        "target": {
            "billing": {"refunds": [{"user_id": 201, "amount": 500.00}]},
            "crm": {"users": [{"user_id": 201, "notes_contains": "partial"}]},
            "email": {"outbox_contains": [{"to": "wei@example.com"}]},
        },
        "max_steps": 8,
    },

    {
        "id": "trap_double_refund",
        "description": (
            "User 202 (Priya Sharma) requests a refund for invoice 2002 ($89.99). "
            "Check the invoice status first. If already refunded, do NOT issue another "
            "refund — instead add a CRM note explaining the invoice was already refunded "
            "and email priya@example.com informing her."
        ),
        "seed": {
            "users": [
                {"user_id": 202, "name": "Priya Sharma", "email": "priya@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "support@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 2002, "user_id": 202, "amount": 89.99,
                 "status": "refunded", "description": "Pro Plan - Already refunded"},
            ],
            "events": [],
        },
        "target": {
            "billing": {"refunds": []},
            "crm": {"users": [{"user_id": 202, "notes_contains": "already refunded"}]},
            "email": {"outbox_contains": [{"to": "priya@example.com"}]},
        },
        "max_steps": 6,
    },

    {
        "id": "trap_order_dependency",
        "description": (
            "User 203 (Marcus Johnson) has a critical service outage. First, escalate "
            "his account (set CRM status to 'escalated', add note 'Critical outage escalated'). "
            "THEN schedule an emergency call titled 'Outage Response - Marcus Johnson' "
            "for 2026-03-08T08:00:00 with marcus@bigclient.com and cto@company.com. "
            "Email both marcus@bigclient.com and cto@company.com."
        ),
        "seed": {
            "users": [
                {"user_id": 203, "name": "Marcus Johnson", "email": "marcus@bigclient.com",
                 "plan": "enterprise", "status": "active",
                 "account_manager": "cto@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 203, "status": "escalated", "notes_contains": "outage"},
            ]},
            "calendar": {"events_min_count": 1},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 10,
    },

    {
        "id": "trap_distractor",
        "description": (
            "User 204 (Elena Kowalski) called on Tuesday at 3:47 PM from her office in "
            "Building C, 4th floor. She mentioned she spoke with Jake from sales last week "
            "who said the new dashboard feature would launch in April. Her actual request: "
            "cancel her upcoming event 1 and email elena@example.com confirming cancellation."
        ),
        "seed": {
            "users": [
                {"user_id": 204, "name": "Elena Kowalski", "email": "elena@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "jake@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [
                {"title": "Elena's Product Demo",
                 "attendees": "elena@example.com,jake@company.com",
                 "datetime": "2026-03-15T14:00:00", "duration_min": 45,
                 "status": "scheduled", "notes": ""},
            ],
        },
        "target": {
            "calendar": {"events": [{"event_id": 1, "status": "cancelled"}]},
            "email": {"outbox_contains": [{"to": "elena@example.com"}]},
        },
        "max_steps": 6,
    },

    {
        "id": "trap_reactivation",
        "description": (
            "User 205 (Daniel Kim) previously churned but now wants to come back. "
            "Reactivate his account: update CRM status from 'churned' to 'active', "
            "upgrade plan to 'pro', add CRM note 'Reactivated - returning customer', "
            "schedule a 'Welcome Back Call' for 2026-03-22T10:00:00 with "
            "daniel@example.com and retention@company.com, and email daniel@example.com."
        ),
        "seed": {
            "users": [
                {"user_id": 205, "name": "Daniel Kim", "email": "daniel@example.com",
                 "plan": "basic", "status": "churned",
                 "account_manager": "retention@company.com", "notes": "Churned 2026-01-15"},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 205, "status": "active", "plan": "pro",
                 "notes_contains": "Reactivated"},
            ]},
            "calendar": {"events_min_count": 1},
            "email": {"outbox_contains": [{"to": "daniel@example.com"}]},
        },
        "max_steps": 10,
    },

    {
        "id": "trap_selective_action",
        "description": (
            "Two users need attention. User 206 (Fatima Al-Rashid) wants a refund of "
            "$199.99 for invoice 2006. User 207 (Chris Taylor) just wants a CRM note "
            "added saying 'Requested feature: bulk export'. Process BOTH requests. "
            "Email fatima@example.com about the refund and chris@example.com confirming "
            "the note."
        ),
        "seed": {
            "users": [
                {"user_id": 206, "name": "Fatima Al-Rashid", "email": "fatima@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "support@company.com", "notes": ""},
                {"user_id": 207, "name": "Chris Taylor", "email": "chris@example.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "support@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 2006, "user_id": 206, "amount": 199.99,
                 "status": "paid", "description": "Pro Plan - March"},
            ],
            "events": [],
        },
        "target": {
            "billing": {"refunds": [{"user_id": 206, "amount": 199.99}]},
            "crm": {"users": [{"user_id": 207, "notes_contains": "bulk export"}]},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 10,
    },

    {
        "id": "trap_missing_event",
        "description": (
            "User 208 (Yuki Tanaka) asks to cancel her 'Team Standup' meeting. "
            "Check the calendar first. If no such event exists, add a CRM note "
            "'No event found to cancel - informed customer' and email "
            "yuki@example.com letting her know."
        ),
        "seed": {
            "users": [
                {"user_id": 208, "name": "Yuki Tanaka", "email": "yuki@example.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "ops@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [{"user_id": 208, "notes_contains": "No event found"}]},
            "email": {"outbox_contains": [{"to": "yuki@example.com"}]},
        },
        "max_steps": 6,
    },

    {
        "id": "trap_refund_then_upgrade",
        "description": (
            "User 209 (Sam Okafor) wants to switch plans. Refund his current invoice "
            "2009 ($149.99), then upgrade his CRM plan from 'basic' to 'enterprise'. "
            "Add CRM note 'Plan switch: refunded basic, upgraded to enterprise'. "
            "Schedule 'Enterprise Kickoff' for 2026-04-01T09:00:00 with "
            "sam@example.com and sales@company.com. Email sam@example.com confirming."
        ),
        "seed": {
            "users": [
                {"user_id": 209, "name": "Sam Okafor", "email": "sam@example.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "sales@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 2009, "user_id": 209, "amount": 149.99,
                 "status": "paid", "description": "Basic Plan - March"},
            ],
            "events": [],
        },
        "target": {
            "billing": {"refunds": [{"user_id": 209, "amount": 149.99}]},
            "crm": {"users": [
                {"user_id": 209, "plan": "enterprise", "notes_contains": "Plan switch"},
            ]},
            "calendar": {"events_min_count": 1},
            "email": {"outbox_contains": [{"to": "sam@example.com"}]},
        },
        "max_steps": 10,
    },

    {
        "id": "trap_bulk_churn",
        "description": (
            "Three users are being offboarded due to company dissolution: "
            "User 210 (Ana Costa), User 211 (Ben Wright), User 212 (Cleo Dubois). "
            "For each: update CRM status to 'churned', add CRM note 'Bulk offboard - company dissolved'. "
            "Send one email to admin@company.com listing all three names."
        ),
        "seed": {
            "users": [
                {"user_id": 210, "name": "Ana Costa", "email": "ana@dissolved.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "admin@company.com", "notes": ""},
                {"user_id": 211, "name": "Ben Wright", "email": "ben@dissolved.com",
                 "plan": "pro", "status": "active",
                 "account_manager": "admin@company.com", "notes": ""},
                {"user_id": 212, "name": "Cleo Dubois", "email": "cleo@dissolved.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "admin@company.com", "notes": ""},
            ],
            "invoices": [],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 210, "status": "churned", "notes_contains": "offboard"},
                {"user_id": 211, "status": "churned", "notes_contains": "offboard"},
                {"user_id": 212, "status": "churned", "notes_contains": "offboard"},
            ]},
            "email": {"outbox_contains": [{"to": "admin@company.com"}]},
        },
        "max_steps": 14,
    },

    {
        "id": "trap_full_lifecycle",
        "description": (
            "Handle the complete lifecycle for user 213 (Rosa Martinez). "
            "Step 1: Upgrade her plan from 'basic' to 'enterprise'. "
            "Step 2: Schedule 'Enterprise Onboarding' for 2026-03-25T10:00:00 with "
            "rosa@example.com and success@company.com. "
            "Step 3: Issue a courtesy credit of $50 refund on invoice 2013. "
            "Step 4: Add CRM note 'Full lifecycle: upgraded, onboarded, credited'. "
            "Step 5: Email rosa@example.com with a summary of all changes. "
            "Step 6: Email success@company.com about the new enterprise customer."
        ),
        "seed": {
            "users": [
                {"user_id": 213, "name": "Rosa Martinez", "email": "rosa@example.com",
                 "plan": "basic", "status": "active",
                 "account_manager": "success@company.com", "notes": ""},
            ],
            "invoices": [
                {"invoice_id": 2013, "user_id": 213, "amount": 99.99,
                 "status": "paid", "description": "Basic Plan - March"},
            ],
            "events": [],
        },
        "target": {
            "crm": {"users": [
                {"user_id": 213, "plan": "enterprise", "notes_contains": "lifecycle"},
            ]},
            "billing": {"refunds": [{"user_id": 213, "amount": 50.00}]},
            "calendar": {"events_min_count": 1},
            "email": {"outbox_min_count": 2},
        },
        "max_steps": 12,
    },
]
