"""Offline Wazuh-format replay acceptance/security tests: only synthetic data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from wazuh_replay import (
    ReplayValidationError,
    validate_replay_file,
    MAX_FILE_BYTES,
    MAX_LINE_BYTES,
    MAX_RECORDS,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "wazuh_training_ssh.jsonl"


def training_record(index: int, minute: int = 0) -> dict:
    return {
        "timestamp": f"2026-11-16T12:{minute:02d}:00.000+0000",
        "id": f"RH-TRAINING-{index}",
        "rule": {"id": "100900", "level": 5, "description": "Fictional SSH event"},
        "agent": {"id": "001", "name": "TRAINING-LINUX-01"},
        "data": {"srcip": "192.0.2.45"},
        "full_log": "VERY-SENSITIVE-DUMMY-TEXT-MUST-NOT-ECHO",
    }


def make_file(tmp_path: Path, objects: list[dict], name="sample.jsonl") -> Path:
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(item) for item in objects) + "\n", encoding="utf-8")
    return path


def test_officially_shaped_example_fixture_stays_offline():
    result = validate_replay_file(FIXTURE)
    assert result["mode"] == "offline-fictional-replay"
    assert result["liveMonitoring"] is False
    assert result["connectedWazuhManager"] is False
    assert result["recordsValidated"] == 3
    assert result["sources"] == ["wazuh-format-synthetic-lab"]
    assert result["correlationCount"] == 1
    assert result["databaseModified"] is False
    correlation = result["correlations"][0]
    assert correlation["matchedEventIds"] == ["RH-TRAINING-1", "RH-TRAINING-2", "RH-TRAINING-3"]
    assert correlation["sourceIp"] == "192.0.2.45"
    rendered = json.dumps(result)
    assert "FICTIONAL RAW LOG MUST NOT LEAVE THE PARSER" not in rendered
    assert "/var/log/auth.log" not in rendered


def test_one_or_two_events_never_generate_positive_match(tmp_path):
    path = make_file(tmp_path, [training_record(1, 0), training_record(2, 2)])
    outcome = validate_replay_file(path)
    assert outcome["recordsValidated"] == 2
    assert outcome["correlationCount"] == 0


def test_temporally_distant_events_are_not_bursts(tmp_path):
    path = make_file(tmp_path, [training_record(1, 0), training_record(2, 10), training_record(3, 20)])
    assert validate_replay_file(path)["correlationCount"] == 0


def test_rejects_duplicate_alerts(tmp_path):
    event = training_record(1)
    path = make_file(tmp_path, [event, event])
    with pytest.raises(ReplayValidationError, match="duplicate"):
        validate_replay_file(path)


@pytest.mark.parametrize("mutate", [
    lambda x: x["agent"].update(name="REAL-HOST-01"),
    lambda x: x["data"].update(srcip="8.8.8.8"),
    lambda x: x["data"].update(srcip="192.168.0.42"),
    lambda x: x["rule"].update(level=100),
    lambda x: x.update(timestamp="not-a-valid-time"),
    lambda x: x.update(agent={"id": "1"}),
])
def test_nonfictional_or_malformed_alerts_are_rejected_without_echo(tmp_path, mutate):
    event = training_record(1)
    mutate(event)
    path = make_file(tmp_path, [event])
    with pytest.raises(ReplayValidationError, match="failed fictional data validation") as exc:
        validate_replay_file(path)
    assert "VERY-SENSITIVE-DUMMY-TEXT-MUST-NOT-ECHO" not in str(exc.value)


def test_no_network_or_db_when_validating(tmp_path):
    path = make_file(tmp_path, [training_record(1)])
    before = {p.name for p in tmp_path.iterdir()}
    result = validate_replay_file(path)
    after = {p.name for p in tmp_path.iterdir()}
    assert before == after
    assert result["databaseModified"] is False


def test_rejects_too_many_records(tmp_path):
    path = make_file(tmp_path, [training_record(i) for i in range(1, MAX_RECORDS + 2)])
    with pytest.raises(ReplayValidationError, match="Too many"):
        validate_replay_file(path)


def test_rejects_line_oversize_even_with_valid_file_size(tmp_path):
    event = training_record(1)
    event["full_log"] = "DUMMY" * (MAX_LINE_BYTES // 4)
    path = make_file(tmp_path, [event])
    assert path.stat().st_size < MAX_FILE_BYTES
    with pytest.raises(ReplayValidationError, match="oversized"):
        validate_replay_file(path)


def test_rejects_invalid_json_without_echoing_contents(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text('{ "full_log": "SENSITIVE-TEST-STRING",  }\n', encoding="utf-8")
    with pytest.raises(ReplayValidationError, match="invalid UTF-8 JSON") as exc:
        validate_replay_file(path)
    assert "SENSITIVE-TEST-STRING" not in str(exc.value)


def test_rejects_wrong_extension_and_symlink(tmp_path):
    json_path = make_file(tmp_path, [training_record(1)], name="not-a-jsonl.json")
    with pytest.raises(ReplayValidationError, match="regular"):
        validate_replay_file(json_path)
    link = tmp_path / "shortcut.jsonl"
    try:
        link.symlink_to(FIXTURE)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable on this host.")
    with pytest.raises(ReplayValidationError, match="non-symlink"):
        validate_replay_file(link)
