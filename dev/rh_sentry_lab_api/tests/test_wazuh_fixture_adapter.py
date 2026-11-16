"""Offline Wazuh JSON-format compatibility fixture tests (never live ingestion)."""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from event_pipeline import generate_scenario
from server import create_app
from wazuh_fixture_adapter import build_wazuh_synthetic_scenario, normalize_wazuh_fixture

PASSWORD = "temporary-local-wazuh-test-password"


def example_alert():
    return {
        "timestamp": "2026-11-16T12:00:00.000+0000",
        "id": "RH-TEST-1",
        "rule": {
            "id": "100900",
            "level": 5,
            "description": "Synthetic SSH login failure",
        },
        "agent": {"id": "001", "name": "TRAINING-LINUX-01"},
        "data": {"srcip": "192.0.2.45"},
        # Unsafe original Wazuh fields are deliberately dropped.
        "full_log": "fake credential secret - raw should never be stored",
        "previous_output": "raw previous output should never be stored",
        "manager": {"name": "TRAINING-MANAGER"},
        "location": "/var/log/auth.log",
    }


def test_fixture_normalization_whitelists_only_trusted_fields():
    result = normalize_wazuh_fixture(example_alert())
    assert result["event_type"] == "wazuh_ssh_failure"
    assert result["source"] == "wazuh-format-synthetic-lab"
    assert result["host"] == "TRAINING-LINUX-01"
    assert result["occurred_at"] == "2026-11-16T12:00:00+00:00"
    assert result["attributes"]["src_ip"] == "192.0.2.45"
    serialized = str(result)
    for excluded in ["fake credential secret", "previous output", "/var/log/auth.log", "TRAINING-MANAGER"]:
        assert excluded not in serialized


@pytest.mark.parametrize("mutation", [
    {"timestamp": "2026-11-16T12:00:00"},  # no timezone
    {"timestamp": "not-a-time"},
    {"rule": {"id": "100900", "level": 99, "description": "SSH"}},
    {"rule": {"id": "100900", "level": True, "description": "SSH"}},
    {"rule": {"id": "notnumeric", "level": 5, "description": "SSH"}},
    {"rule": {"id": "100900", "level": 5}},
    {"agent": {"id": "001", "name": "real-customer-host"}},
    {"agent": {"id": "unexpected", "name": "TRAINING-LINUX-01"}},
    {"data": {"srcip": "8.8.8.8"}},
    {"data": {"srcip": "not-an-IP"}},
    {"data": {}},
    {"agent": "not-an-object"},
    {"id": "contains\nnewline"},
])
def test_malformed_or_nonfictional_wazuh_inputs_fail(mutation):
    alert = example_alert()
    alert.update(mutation)
    with pytest.raises(ValueError):
        normalize_wazuh_fixture(alert)


def test_burst_and_single_example_do_not_overclaim_detection():
    t = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
    burst, correlations = build_wazuh_synthetic_scenario("wazuh-ssh-burst", t)
    assert len(burst) == 3
    assert len(correlations) == 1
    assert correlations[0]["rule_id"] == "RHS-WAZ-SYN-001"
    assert correlations[0]["case_id"] is None
    assert correlations[0]["event_offsets"] == [0, 1, 2]
    assert len({event["attributes"]["wazuh_alert_id"] for event in burst}) == 3
    single, no_correlations = build_wazuh_synthetic_scenario("wazuh-ssh-benign", t)
    assert len(single) == 1
    assert no_correlations == []
    assert generate_scenario("wazuh-ssh-benign", "alderwick", t)[1] == []


@pytest.fixture
def lab(tmp_path: Path):
    db_path = tmp_path / "wazuh-fixture-lab.sqlite3"
    with TestClient(create_app(db_path, PASSWORD)) as http:
        yield http, db_path


def login(http, username):
    response = http.post("/api/lab/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["csrfToken"]


def submit(http, csrf, tenant, scenario, token):
    return http.post(
        f"/api/tenants/{tenant}/lab/scenarios/ingest",
        headers={"X-CSRF-Token": csrf},
        json={"scenarioId": scenario, "idempotencyKey": token},
    )


def test_wazuh_format_events_saved_with_provenance_and_without_raw_log(lab):
    http, db_path = lab
    csrf = login(http, "alderwick-analyst")
    result = submit(http, csrf, "alderwick", "wazuh-ssh-burst", "wazuh-batch-0001")
    assert result.status_code == 201, result.text
    assert result.json()["eventCount"] == 3
    assert result.json()["correlationCount"] == 1
    events = http.get("/api/tenants/alderwick/lab/events").json()["items"]
    assert len(events) == 3
    assert all(event["source"] == "wazuh-format-synthetic-lab" for event in events)
    assert all(event["attributes"]["wazuh_rule_id"] == "100900" for event in events)
    match = http.get("/api/tenants/alderwick/lab/correlations").json()["items"][0]
    assert set(match["eventIds"]) == {event["id"] for event in events}
    assert match["caseId"] is None
    with sqlite3.connect(db_path) as db:
        contents = " ".join(row[0] for row in db.execute(
            "SELECT attributes_json FROM synthetic_events WHERE tenant_id='alderwick'"
        ))
        assert "full_log" not in contents
        assert "credential" not in contents
        assert "/var/log/auth.log" not in contents
    # Does not rewrite pre-existing incident records.
    assert http.get("/api/tenants/alderwick/incidents/SEN-2047").json()["version"] == 1


def test_idempotency_and_cross_tenant_isolation_for_wazuh_style_events(lab):
    http, db_path = lab
    csrf = login(http, "alderwick-analyst")
    first = submit(http, csrf, "alderwick", "wazuh-ssh-benign", "wazuh-token-0001")
    assert first.status_code == 201
    assert first.json()["correlationCount"] == 0
    again = submit(http, csrf, "alderwick", "wazuh-ssh-benign", "wazuh-token-0001")
    assert again.status_code == 200
    assert again.json()["replayed"] is True
    assert submit(http, csrf, "alderwick", "wazuh-ssh-burst", "wazuh-token-0001").status_code == 409
    assert submit(http, csrf, "summit", "wazuh-ssh-burst", "foreign-token-0001").status_code == 404
    assert http.get("/api/tenants/summit/lab/events").status_code == 404
    assert http.get("/api/tenants/summit/lab/correlations").status_code == 404
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM synthetic_event_batches").fetchone()[0] == 1


def test_wazuh_scenario_viewer_is_not_allowed(lab):
    http, _ = lab
    csrf = login(http, "alderwick-viewer")
    assert submit(http, csrf, "alderwick", "wazuh-ssh-burst", "viewer-token-001").status_code == 403
    assert http.get("/api/tenants/alderwick/lab/events").status_code == 403
