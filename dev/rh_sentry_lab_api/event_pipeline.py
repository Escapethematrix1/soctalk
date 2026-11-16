"""Deterministic RH Sentry training-lab event fixtures only.

IMPORTANT: no collectors, network traffic, shell tools or real telemetry.
Scenario ID is the only event-content input; arbitrary user-provided logs
and security events are deliberately not accepted by this lab.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypedDict


class SyntheticEvent(TypedDict):
    event_type: str
    occurred_at: str
    source: str
    actor: str
    host: str
    description: str
    attributes: dict[str, str | int | bool]


class Correlation(TypedDict):
    rule_id: str
    title: str
    explanation: str
    case_id: str | None
    event_offsets: list[int]


SCENARIOS: dict[str, dict[str, str]] = {
    "impossible-travel": {
        "name": "Unusual consecutive sign-ins",
        "description": "Two fictional cloud identity sign-ins four minutes apart.",
    },
    "encoded-powershell": {
        "name": "Encoded PowerShell from suspicious parent",
        "description": "One fictional endpoint process event with an encoded command indicator.",
    },
    "ordinary-signins": {
        "name": "Normal sign-ins (no correlation)",
        "description": "Two fictional sign-ins from the same location, 30 minutes apart.",
    },
    "partial-auth": {
        "name": "Incomplete sign-in telemetry",
        "description": "One fictional login with missing distance context. No positive correlation.",
    },
    "wazuh-ssh-burst": {
        "name": "Wazuh-format SSH failure burst",
        "description": "Three fabricated Wazuh JSON alerts, normalized and matched by agent, rule, source and time.",
    },
    "wazuh-ssh-benign": {
        "name": "Wazuh-format single SSH failure",
        "description": "One fabricated Wazuh alert; insufficient evidence for a burst correlation.",
    },
}


def scenario_catalogue() -> list[dict[str, str]]:
    return [{"id": key, **value} for key, value in SCENARIOS.items()]


def _iso(time_value: datetime) -> str:
    return time_value.astimezone(timezone.utc).isoformat(timespec="seconds")


def generate_scenario(
    scenario_id: str, tenant_id: str, now: datetime | None = None
) -> tuple[list[SyntheticEvent], list[Correlation]]:
    """Return a synthetic batch and conservative deterministic match results.

    Rule matches are illustrative *correlations*, never incident detections.
    Pre-existing example cases may be referenced but are never modified here.
    """
    if scenario_id not in SCENARIOS:
        raise ValueError("Unknown synthetic scenario.")
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        raise ValueError("Synthetic scenario time must be timezone aware.")

    def event(
        event_type: str, minutes_ago: int, description: str,
        attributes: dict[str, str | int | bool]
    ) -> SyntheticEvent:
        return {
            "event_type": event_type,
            "occurred_at": _iso(base - timedelta(minutes=minutes_ago)),
            "source": "rh-sentry-synthetic-lab",
            "actor": "training-account@demo.invalid",
            "host": "TRAINING-DEVICE-01",
            "description": description,
            "attributes": attributes,
        }

    if scenario_id in ("wazuh-ssh-burst", "wazuh-ssh-benign"):
        # Deferred import avoids a circular reference with the fixture schema
        # and lets the existing synthetic ingestion endpoint keep its contract.
        from wazuh_fixture_adapter import build_wazuh_synthetic_scenario
        return build_wazuh_synthetic_scenario(scenario_id, base)

    if scenario_id == "impossible-travel":
        events = [
            event("identity_sign_in", 7, "Fictional sign-in: Region A.", {
                "identity": "training-account@demo.invalid", "region": "Region A",
                "minutes_from_previous": 0, "distance_km": 0,
            }),
            event("identity_sign_in", 3, "Fictional sign-in: Region B.", {
                "identity": "training-account@demo.invalid", "region": "Region B",
                "minutes_from_previous": 4, "distance_km": 2900,
            }),
        ]
        # Explicit conditions make it obvious why the example matched.
        second = events[1]["attributes"]
        correlated = (
            second["minutes_from_previous"] < 15
            and second["distance_km"] > 500
            and events[0]["attributes"]["identity"] == second["identity"]
        )
        correlations: list[Correlation] = []
        if correlated:
            correlations.append({
                "rule_id": "RHS-DET-001",
                "title": "Synthetic impossible travel example",
                "explanation": "Two fake sign-ins share an account, with 4 minutes and 2900 km between them. Requires real analyst corroboration in production.",
                "case_id": "SEN-2048" if tenant_id == "alderwick" else None,
                "event_offsets": [0, 1],
            })
        return events, correlations

    if scenario_id == "encoded-powershell":
        events = [event("endpoint_process", 2, "Fictional encoded PowerShell process.", {
            "encoded_command": True, "parent_trusted": False,
            "process_name": "powershell.exe", "command_line": "redacted-synthetic-command",
        })]
        f = events[0]["attributes"]
        correlations = [{
            "rule_id": "RHS-DET-002", "title": "Synthetic encoded PowerShell example",
            "explanation": "A fictional encoded-command flag and an untrusted parent indicator matched a demonstration predicate.",
            "case_id": "SEN-2047" if tenant_id == "alderwick" else None,
            "event_offsets": [0],
        }] if f["encoded_command"] is True and f["parent_trusted"] is False else []
        return events, correlations

    if scenario_id == "ordinary-signins":
        events = [
            event("identity_sign_in", 35, "Ordinary fictional sign-in A.", {
                "identity": "training-account@demo.invalid", "region": "Region A",
                "minutes_from_previous": 0, "distance_km": 0,
            }),
            event("identity_sign_in", 5, "Ordinary fictional sign-in B.", {
                "identity": "training-account@demo.invalid", "region": "Region A",
                "minutes_from_previous": 30, "distance_km": 0,
            }),
        ]
        return events, []

    return [event("identity_sign_in", 2, "Fictional login with incomplete geolocation.", {
        "identity": "training-account@demo.invalid", "region": "Unknown",
        "minutes_from_previous": 4,
    })], []
