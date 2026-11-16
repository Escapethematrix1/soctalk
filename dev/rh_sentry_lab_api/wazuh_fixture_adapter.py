"""Strict, offline Wazuh alert-format adapter for RH Sentry training fixtures.

This module does NOT connect to Wazuh, read alerts.json, import user-supplied
logs, run commands, or represent live endpoint data. All accepted source
objects are manufactured by the fixture generator in this package. A future
real connector needs an entirely separate authenticated ingestion boundary.

Wazuh-compatible sample fields are based on the documented JSON alert shape:
timestamp, id, rule.id/level/description, agent.id/name and data.srcip.
Untrusted full_log, previous_output, arbitrary decoded data and raw JSON are
never persisted by this adapter.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network, IPv4Address
from typing import Any, Mapping

from event_pipeline import SyntheticEvent, Correlation


def _text(value: Any, name: str, *, maximum: int = 120) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or any(
        ord(ch) < 32 for ch in value
    ):
        raise ValueError(f"Invalid Wazuh fixture field: {name}.")
    return value


def _subobject(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Missing Wazuh fixture object: {key}.")
    return value


def _timestamp(value: Any) -> str:
    source = _text(value, "timestamp", maximum=60)
    try:
        parsed = datetime.fromisoformat(source.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid Wazuh fixture timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValueError("A timezone offset is required for Wazuh fixture timestamps.")
    if parsed.year < 2020 or parsed.year > 2100:
        raise ValueError("Wazuh fixture timestamp outside supported lab range.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def normalize_wazuh_fixture(alert: Mapping[str, Any]) -> SyntheticEvent:
    """Reduce one manufactured Wazuh-style alert to safe normalized fields.

    Unknown source keys are deliberately ignored instead of preserved.
    This is not validation suitable for real Wazuh feeds.
    """
    if not isinstance(alert, dict):
        raise ValueError("Wazuh fixture must be an object.")
    rule = _subobject(alert, "rule")
    agent = _subobject(alert, "agent")
    data = _subobject(alert, "data")
    rule_id = _text(rule.get("id"), "rule.id", maximum=16)
    if not rule_id.isdecimal():
        raise ValueError("Wazuh fixture rule ID must be numeric.")
    level = rule.get("level")
    if type(level) is not int or not (0 <= level <= 15):
        raise ValueError("Wazuh fixture rule level must be 0–15.")
    explanation = _text(rule.get("description"), "rule.description", maximum=140)
    agent_id = _text(agent.get("id"), "agent.id", maximum=16)
    if not agent_id.isdecimal():
        raise ValueError("Wazuh fixture agent ID must be numeric.")
    agent_name = _text(agent.get("name"), "agent.name", maximum=60)
    event_id = _text(alert.get("id"), "id", maximum=55)
    src_ip = _text(data.get("srcip"), "data.srcip", maximum=45)
    try:
        ip = ip_address(src_ip)
    except ValueError as exc:
        raise ValueError("Invalid Wazuh fixture source IP.") from exc
    # Hard restriction for this public repository's fixtures: never use a
    # genuine routable source IP or a genuine endpoint name.
    # Use TEST-NET-1 only, keeping all scenario data obviously fictional.
    if not isinstance(ip, IPv4Address) or ip not in ip_network("192.0.2.0/24"):
        raise ValueError("Wazuh training fixture source IP must be TEST-NET-1.")
    if not agent_name.startswith("TRAINING-"):
        raise ValueError("Only fictional TRAINING hosts are accepted.")
    return {
        "event_type": "wazuh_ssh_failure",
        "occurred_at": _timestamp(alert.get("timestamp")),
        "source": "wazuh-format-synthetic-lab",
        "actor": "training-user@demo.invalid",
        "host": agent_name,
        "description": explanation,
        "attributes": {
            "wazuh_rule_id": rule_id,
            "wazuh_rule_level": level,
            "wazuh_agent_id": agent_id,
            "wazuh_alert_id": event_id,
            "src_ip": str(ip),
        },
    }


def build_wazuh_synthetic_scenario(
    scenario_id: str,
    base: datetime,
) -> tuple[list[SyntheticEvent], list[Correlation]]:
    """Manufacture Wazuh-shaped SSH examples, then normalise and correlate.

    The alert rule ID 100900 is invented for this lab; it must not be
    confused with a default Wazuh rule or certified detection.
    """
    if base.tzinfo is None:
        raise ValueError("Synthetic timestamp must be timezone-aware.")
    if scenario_id not in ("wazuh-ssh-burst", "wazuh-ssh-benign"):
        raise ValueError("Unknown Wazuh training scenario.")
    offsets = [4, 3, 2] if scenario_id == "wazuh-ssh-burst" else [4]
    alerts = []
    for i, minutes in enumerate(offsets):
        alerts.append({
            "timestamp": (base - timedelta(minutes=minutes)).isoformat(),
            "id": f"RH-TEST-{i+1}",
            "rule": {
                "id": "100900",
                "level": 5,
                "description": "Synthetic SSH login failure in isolated training host",
            },
            "agent": {"id": "001", "name": "TRAINING-LINUX-01"},
            "data": {"srcip": "192.0.2.45"},
            # Intentionally unsafe original fields are never retained:
            "full_log": "never persist this raw example log",
            "previous_output": "never persist previous output",
        })
    normalized = [normalize_wazuh_fixture(alert) for alert in alerts]
    # Require at least 3 distinct example event IDs, matching agent/rule/IP,
    # within 5 minutes. Unknown/partial data cannot correlate.
    matches: list[Correlation] = []
    if len(normalized) >= 3:
        timestamps = [datetime.fromisoformat(e["occurred_at"]) for e in normalized]
        same_key = {
            (e["attributes"]["wazuh_agent_id"], e["attributes"]["wazuh_rule_id"],
             e["attributes"]["src_ip"]) for e in normalized
        }
        event_ids = {e["attributes"]["wazuh_alert_id"] for e in normalized}
        if len(same_key) == 1 and len(event_ids) == len(normalized) and max(timestamps) - min(timestamps) <= timedelta(minutes=5):
            matches.append({
                "rule_id": "RHS-WAZ-SYN-001",
                "title": "Synthetic Wazuh-format SSH failure burst",
                "explanation": "Three fictional SSH alert records share the same agent, rule and TEST-NET source within five minutes. This is not proof of an attack.",
                "case_id": None,
                "event_offsets": list(range(len(normalized))),
            })
    return normalized, matches
