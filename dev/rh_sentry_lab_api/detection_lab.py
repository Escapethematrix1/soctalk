"""Allowlisted deterministic detection predicates for RH Sentry's synthetic lab.

Only fictional, already-stored synthetic events are allowed as input. There is
no user-defined query execution, regex, Python evaluation, shell command,
network access, or automatic incident creation. These are instructional
predicates, NOT operationally verified detections.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

RULE_TEMPLATES: dict[str, dict[str, Any]] = {
    "identity_travel": {
        "title": "Unusual identity travel",
        "description": "Synthetic sign-ins for one identity from different regions within 15 minutes.",
        "threshold": 500,
        "thresholdUnit": "minimum distance (km)",
        "minThreshold": 100,
        "maxThreshold": 5000,
    },
    "encoded_powershell": {
        "title": "Encoded PowerShell with untrusted parent",
        "description": "Synthetic process marked encoded_command=true and parent_trusted=false.",
        "threshold": 1,
        "thresholdUnit": "boolean predicate (fixed)",
        "minThreshold": 1,
        "maxThreshold": 1,
    },
    "wazuh_ssh_burst": {
        "title": "Wazuh-format SSH failure burst",
        "description": "Three or more fictional SSH failures from one agent, rule and TEST-NET address within five minutes.",
        "threshold": 3,
        "thresholdUnit": "minimum failures (5-minute window)",
        "minThreshold": 3,
        "maxThreshold": 20,
    },
}


def validate_threshold(kind: str, value: int) -> None:
    if kind not in RULE_TEMPLATES:
        raise ValueError("Unsupported detection strategy.")
    template = RULE_TEMPLATES[kind]
    if type(value) is not int or not template["minThreshold"] <= value <= template["maxThreshold"]:
        raise ValueError("Threshold outside the safe range for this strategy.")


def _stamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Synthetic event timestamp must be timezone-aware.")
    return parsed


def evaluate(kind: str, threshold: int, events: list[dict[str, Any]]) -> list[int]:
    """Return database event IDs supporting ONE explainable positive outcome.

    No positive result may be produced from incomplete input or mixed batches.
    """
    validate_threshold(kind, threshold)
    if len(events) > 25:
        raise ValueError("Synthetic test batch exceeds bounded lab limits.")

    if kind == "encoded_powershell":
        for event in events:
            attrs = event["attributes"]
            if (event["event_type"] == "endpoint_process"
                    and attrs.get("encoded_command") is True
                    and attrs.get("parent_trusted") is False):
                return [int(event["id"])]
        return []

    if kind == "identity_travel":
        ordered = sorted(
            (ev for ev in events if ev["event_type"] == "identity_sign_in"),
            key=lambda ev: ev["occurred_at"],
        )
        for position, first in enumerate(ordered):
            first_attrs = first["attributes"]
            identity = first_attrs.get("identity")
            region = first_attrs.get("region")
            if not isinstance(identity, str) or not identity or not isinstance(region, str) or region == "Unknown":
                continue
            for second in ordered[position + 1:]:
                second_attrs = second["attributes"]
                if (second_attrs.get("identity") != identity
                        or not isinstance(second_attrs.get("region"), str)
                        or second_attrs.get("region") in ("Unknown", region)):
                    continue
                minutes = second_attrs.get("minutes_from_previous")
                distance = second_attrs.get("distance_km")
                if (type(minutes) is not int or type(distance) is not int
                        or not 0 < minutes <= 15 or distance < threshold):
                    continue
                delta = _stamp(second["occurred_at"]) - _stamp(first["occurred_at"])
                if timedelta(0) < delta <= timedelta(minutes=15):
                    return [int(first["id"]), int(second["id"])]
        return []

    # Wazuh-format training fixtures only. Require distinct alert IDs, same
    # agent, rule and TEST-NET source, and a bounded 5-minute occurrence window.
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for event in events:
        if event["event_type"] != "wazuh_ssh_failure":
            continue
        attrs = event["attributes"]
        agent, rule, source, alert_id = (
            attrs.get("wazuh_agent_id"), attrs.get("wazuh_rule_id"),
            attrs.get("src_ip"), attrs.get("wazuh_alert_id"),
        )
        if not all(isinstance(field, str) and field for field in (agent, rule, source, alert_id)):
            continue
        if not source.startswith("192.0.2."):
            continue
        groups.setdefault((agent, rule, source), []).append(event)
    for group in groups.values():
        ordered = sorted(group, key=lambda event: event["occurred_at"])
        for i in range(len(ordered) - threshold + 1):
            window = ordered[i:i + threshold]
            if len({event["attributes"]["wazuh_alert_id"] for event in window}) != threshold:
                continue
            delta = _stamp(window[-1]["occurred_at"]) - _stamp(window[0]["occurred_at"])
            if timedelta(0) <= delta <= timedelta(minutes=5):
                return [int(event["id"]) for event in window]
    return []
