"""RH Sentry response approval templates; no executable actions.

Every playbook is a fictional planning prompt. An 'approved' lab request is
approval only for a locally recorded dry-run receipt. It CANNOT reach an
endpoint, change an account, perform a network request or run a command.
"""
from __future__ import annotations

PLAYBOOKS = {
    "identity_review": {
        "name": "Verify unusual sign-in",
        "purpose": "Confirm identity, account owner and sign-in context before proposing any response.",
        "impact": "Review and communication only. No session revocation.",
        "steps": [
            "Confirm case evidence and the affected fictional identity",
            "Verify whether the activity was approved",
            "Document findings and decide whether escalation is necessary",
        ],
        "responseClass": "manual_investigation",
    },
    "process_review": {
        "name": "Review suspicious process",
        "purpose": "Assess a fictional execution event before any proposed containment.",
        "impact": "Review only. No process termination or endpoint isolation.",
        "steps": [
            "Review process and parent process evidence",
            "Check available event provenance and uncertainty",
            "Document whether additional analysis is required",
        ],
        "responseClass": "manual_investigation",
    },
    "session_revocation": {
        "name": "Plan identity session revocation",
        "purpose": "Prepare a human-approved plan for a fictional compromised-account scenario.",
        "impact": "A real implementation could interrupt user sessions; never executed by this lab.",
        "steps": [
            "Confirm account owner and incident scope",
            "Assess business interruption and recovery requirements",
            "Request independent lead approval for simulation",
        ],
        "responseClass": "disruptive_plan",
    },
    "endpoint_isolation": {
        "name": "Plan endpoint isolation",
        "purpose": "Review the potential impact of isolating a fictional device.",
        "impact": "A real implementation could disconnect an asset; never executed by this lab.",
        "steps": [
            "Confirm affected asset and evidence source",
            "Review business services and emergency access",
            "Request independent lead approval for simulation",
        ],
        "responseClass": "disruptive_plan",
    },
}


def catalogue() -> list[dict]:
    return [
        {"id": key, **value, "executable": False, "dryRunOnly": True}
        for key, value in PLAYBOOKS.items()
    ]
