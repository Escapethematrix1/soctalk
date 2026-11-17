"""Offline pre-connection validation for *fictional* Wazuh JSON-lines samples.

No network access, no HTTP endpoints, no database writes, no credentials, no
agent control and NO actual Wazuh manager connection. Real alerts are rejected
by the training-only address and host restrictions in wazuh_fixture_adapter.
Only redacted, manufactured training files are suitable as input.

Run: python wazuh_replay.py --file fixtures/wazuh_training_ssh.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from wazuh_fixture_adapter import normalize_wazuh_fixture

MAX_FILE_BYTES = 256 * 1024
MAX_RECORDS = 25
MAX_LINE_BYTES = 8 * 1024
CORRELATION_WINDOW = timedelta(minutes=5)


class ReplayValidationError(ValueError):
    """Safe, generic error; never include untrusted line contents."""


def _load_training_lines(path: Path) -> list[Mapping[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".jsonl":
        raise ReplayValidationError("Expected a regular, non-symlink .jsonl training file.")
    if path.stat().st_size == 0 or path.stat().st_size > MAX_FILE_BYTES:
        raise ReplayValidationError("Training file is empty or exceeds size limit.")
    items: list[Mapping[str, Any]] = []
    try:
        with path.open("rb") as handle:
            for number, line in enumerate(handle, start=1):
                if number > MAX_RECORDS:
                    raise ReplayValidationError("Too many fictional alerts in training file.")
                if not line.strip() or len(line) > MAX_LINE_BYTES:
                    raise ReplayValidationError(f"Training record {number}: empty or oversized.")
                try:
                    record = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ReplayValidationError(f"Training record {number}: invalid UTF-8 JSON.") from error
                if not isinstance(record, dict):
                    raise ReplayValidationError(f"Training record {number}: expected a JSON object.")
                items.append(record)
    except OSError as error:
        raise ReplayValidationError("Unable to read local training file.") from error
    return items


def _safe_normalize(items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for index, item in enumerate(items, start=1):
        try:
            normalized = normalize_wazuh_fixture(item)
        except (ValueError, TypeError, KeyError) as error:
            # Do not include the original field/error text; it could be a
            # real log, username or secret accidentally supplied by a user.
            raise ReplayValidationError(
                f"Training record {index}: failed fictional data validation."
            ) from error
        attributes = normalized["attributes"]
        identity = (str(attributes["wazuh_agent_id"]), str(attributes["wazuh_alert_id"]))
        if identity in identities:
            raise ReplayValidationError(f"Training record {index}: duplicate alert identifier.")
        identities.add(identity)
        output.append(normalized)
    return output


def _correlation_summaries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Conservative time-window rule for fabricated SSH failures.

    This does not signify maliciousness or assign an operational severity.
    """
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event["event_type"] != "wazuh_ssh_failure":
            continue
        attrs = event["attributes"]
        key = (str(attrs["wazuh_agent_id"]), str(attrs["wazuh_rule_id"]), str(attrs["src_ip"]))
        groups[key].append(event)

    results = []
    for (agent_id, rule_id, ip), rows in sorted(groups.items()):
        ordered = sorted(rows, key=lambda row: row["occurred_at"])
        matching_ids: list[str] | None = None
        for i in range(len(ordered) - 2):
            window = ordered[i : i + 3]
            oldest = datetime.fromisoformat(window[0]["occurred_at"])
            latest = datetime.fromisoformat(window[2]["occurred_at"])
            if latest - oldest <= CORRELATION_WINDOW:
                matching_ids = [str(row["attributes"]["wazuh_alert_id"]) for row in window]
                break
        if matching_ids:
            results.append({
                "ruleId": "RHS-WAZ-SYN-001",
                "agentId": agent_id,
                "wazuhRuleId": rule_id,
                "sourceIp": ip,   # always TEST-NET-1 by adapter validation
                "matchedEventIds": matching_ids,
                "conclusion": "Synthetic training correlation only; not a confirmed attack.",
            })
    return results


def validate_replay_file(path: Path) -> dict[str, Any]:
    """Return a small, safe in-memory report. No raw log text is echoed or saved."""
    records = _load_training_lines(path)
    normalized = _safe_normalize(records)
    correlations = _correlation_summaries(normalized)
    return {
        "mode": "offline-fictional-replay",
        "liveMonitoring": False,
        "connectedWazuhManager": False,
        "recordsValidated": len(normalized),
        "sources": sorted({event["source"] for event in normalized}),
        "correlationCount": len(correlations),
        "correlations": correlations,
        "databaseModified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline RH Sentry fictional Wazuh-format JSONL validation; never imports real logs."
    )
    parser.add_argument("--file", type=Path, required=True, help="Path to fictional .jsonl training sample.")
    args = parser.parse_args()
    try:
        result = validate_replay_file(args.file)
    except ReplayValidationError as error:
        parser.exit(2, f"Rejected fictional replay: {error}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
