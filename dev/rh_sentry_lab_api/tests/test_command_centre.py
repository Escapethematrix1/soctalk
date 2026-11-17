"""Tenant-scoped Command Centre summary; fictional lab only."""
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from server import create_app

PASSWORD = "rh-sentry-overview-test-password"


@pytest.fixture
def lab(tmp_path: Path):
    db_path = tmp_path / "overview.sqlite3"
    with TestClient(create_app(db_path, PASSWORD)) as client:
        yield client, db_path


def login(client: TestClient, username: str) -> str:
    result = client.post("/api/lab/login", json={"username": username, "password": PASSWORD})
    assert result.status_code == 200, result.text
    return result.json()["csrfToken"]


def overview(client: TestClient, tenant="alderwick"):
    return client.get(f"/api/tenants/{tenant}/lab/overview")


def test_summary_requires_authentication(lab):
    client, _ = lab
    assert overview(client).status_code == 401


def test_analyst_sees_only_own_tenant_persisted_incidents(lab):
    client, _ = lab
    login(client, "alderwick-analyst")
    response = overview(client)
    assert response.status_code == 200
    result = response.json()
    assert result["tenantId"] == "alderwick"
    assert result["tenantName"] == "Alderwick Logistics"
    assert result["source"] == "local-sqlite-fictional"
    assert result["liveTelemetry"] is False
    assert result["liveSensors"] == 0
    assert result["liveCoveragePercent"] == 0
    assert result["aiAnalysisConnected"] is False
    assert result["incidentSummary"] == {
        "total": 2, "open": 2, "critical": 1,
        "high": 1, "assigned": 0,
        "byStatus": {"investigating": 1, "triage": 1},
    }
    assert {x["id"] for x in result["recentIncidents"]} == {"SEN-2048", "SEN-2047"}
    assert result["syntheticEventCount"] == 0
    assert result["syntheticCorrelationCount"] == 0
    assert overview(client, "harbourline").status_code == 404
    assert overview(client, "summit").status_code == 404


def test_viewer_receives_incident_summary_but_not_internal_event_totals(lab):
    client, _ = lab
    login(client, "alderwick-viewer")
    response = overview(client)
    assert response.status_code == 200
    body = response.json()
    assert body["incidentSummary"]["total"] == 2
    assert body["syntheticEventCount"] is None
    assert body["syntheticCorrelationCount"] is None
    assert body["liveSensors"] == 0
    assert all(entry["tenantId"] == "alderwick" for entry in body["recentIncidents"])
    assert overview(client, "summit").status_code == 404


def test_auditor_cannot_read_customer_dashboard(lab):
    client, _ = lab
    login(client, "lab-auditor")
    assert overview(client).status_code == 404


def test_dashboard_reflects_saved_case_state_and_new_synthetic_events(lab):
    client, db_path = lab
    csrf = login(client, "alderwick-analyst")
    case = client.patch(
        "/api/tenants/alderwick/incidents/SEN-2047",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "status": "investigating",
              "assignedTo": "alderwick-lead"},
    )
    assert case.status_code == 200, case.text
    event = client.post(
        "/api/tenants/alderwick/lab/scenarios/ingest",
        headers={"X-CSRF-Token": csrf},
        json={"scenarioId": "impossible-travel", "idempotencyKey": "overview-batch-0001"},
    )
    assert event.status_code == 201, event.text
    counts = overview(client).json()
    assert counts["incidentSummary"]["assigned"] == 1
    assert counts["incidentSummary"]["byStatus"] == {"investigating": 2}
    assert counts["syntheticEventCount"] == 2
    assert counts["syntheticCorrelationCount"] == 1
    assert next(x for x in counts["recentIncidents"] if x["id"] == "SEN-2047")["version"] == 2
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 6
    # No mutation occurred merely by fetching the Command Centre.
    before = overview(client).json()
    after = overview(client).json()
    assert before["incidentSummary"] == after["incidentSummary"]


def test_no_disclosure_when_changing_session_to_other_customer(lab):
    client, _ = lab
    login(client, "alderwick-analyst")
    assert overview(client).json()["incidentSummary"]["critical"] == 1
    login(client, "summit-viewer")
    assert overview(client, "alderwick").status_code == 404
    summit = overview(client, "summit")
    assert summit.status_code == 200
    assert summit.json()["incidentSummary"]["critical"] == 0
    assert {x["id"] for x in summit.json()["recentIncidents"]} == {"SEN-2046", "SEN-2043"}
