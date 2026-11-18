"""Incident guided work context: membership, evidence and response provenance."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from server import create_app

PASSWORD = "incident-context-only-lab-pass-2026"


@pytest.fixture
def lab(tmp_path: Path):
    db = tmp_path / "guided-cases.sqlite3"
    with TestClient(create_app(db, PASSWORD)) as client:
        yield client, db


def login(client, user="alderwick-analyst"):
    response = client.post("/api/lab/login", json={"username": user, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["csrfToken"]


def context(tenant="alderwick", case="SEN-2047"):
    return f"/api/tenants/{tenant}/incidents/{case}/work-context"


def test_context_is_fictional_analyst_only_and_tenant_scoped(lab):
    client, _ = lab
    assert client.get(context()).status_code == 401
    login(client, "alderwick-viewer")
    assert client.get(context()).status_code == 403
    login(client)
    assert client.get(context("summit", "SEN-2046")).status_code == 404
    assert client.get(context("alderwick", "SEN-2046")).status_code == 404
    assert client.get(context("alderwick", "SEN-NOT-THERE")).status_code == 404
    result = client.get(context())
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["tenantId"] == "alderwick"
    assert data["incidentId"] == "SEN-2047"
    assert data["incidentVersion"] == 1
    assert data["evidence"] == {"analystNoteCount": 0, "verifiedTelemetryCount": 0}
    assert data["responses"] == {
        "pending": 0, "approvedDryRun": 0, "rejected": 0, "recordedDryRuns": 0
    }
    assert data["dataSource"] == "local-sqlite-fictional"
    assert data["aiInference"] is False
    assert data["liveTelemetry"] is False
    assert data["responseExecution"] is False
    assert {item["id"] for item in data["assets"]} == {"AST-ALD-001"}
    assert all(item["monitoringState"] == "not_connected" for item in data["assets"])


def test_context_reflects_real_sqlite_note_and_response_proposal(lab):
    client, db = lab
    csrf = login(client)
    added = client.post("/api/tenants/alderwick/incidents/SEN-2047/evidence",
        headers={"X-CSRF-Token": csrf}, json={
            "expectedVersion": 1,
            "note": "Fictional parent process needs independent validation."
        })
    assert added.status_code == 201, added.text
    proposed = client.post("/api/tenants/alderwick/lab/response-requests",
        headers={"X-CSRF-Token": csrf}, json={
            "incidentId": "SEN-2047",
            "playbookId": "process_review",
            "idempotencyKey": "context-response-proposal-001",
            "reason": "Review the fictional execution evidence before proceeding."
        })
    assert proposed.status_code == 201, proposed.text
    data = client.get(context()).json()
    assert data["incidentVersion"] == 2
    assert data["evidence"]["analystNoteCount"] == 1
    assert data["responses"]["pending"] == 1
    assert data["caseChangeCount"] == 1
    lead_csrf = login(client, "alderwick-lead")
    decision = client.post(
        f"/api/tenants/alderwick/lab/response-requests/{proposed.json()['id']}/decision",
        headers={"X-CSRF-Token": lead_csrf},
        json={"expectedVersion": 1, "decision": "approve_dry_run",
              "reason": "Fictional evidence reviewed independently and scope confirmed."}
    )
    assert decision.status_code == 200, decision.text
    receipt = client.post(
        f"/api/tenants/alderwick/lab/response-requests/{proposed.json()['id']}/simulate",
        headers={"X-CSRF-Token": lead_csrf}, json={"expectedVersion": 2}
    )
    assert receipt.status_code == 200, receipt.text
    status = client.get(context()).json()
    assert status["responses"] == {
        "pending": 0, "approvedDryRun": 1, "rejected": 0, "recordedDryRuns": 1
    }
    with TestClient(create_app(db, PASSWORD)) as reopened:
        login(reopened)
        persisted = reopened.get(context()).json()
        assert persisted["evidence"]["analystNoteCount"] == 1
        assert persisted["responses"]["recordedDryRuns"] == 1
        assert persisted["incidentVersion"] == 2
        assert persisted["liveTelemetry"] is False


def test_context_uses_same_tenant_for_case_asset_links(lab):
    client, _ = lab
    token = login(client)
    before = client.get(context()).json()
    assert len(before["assets"]) == 1
    linked = client.post("/api/tenants/alderwick/assets/AST-ALD-003/incidents",
        headers={"X-CSRF-Token": token},
        json={"expectedVersion": 1, "incidentId": "SEN-2047"})
    assert linked.status_code == 201, linked.text
    after = client.get(context()).json()
    assert {item["id"] for item in after["assets"]} == {"AST-ALD-001", "AST-ALD-003"}
    other = client.get(context("alderwick", "SEN-2048")).json()
    assert "AST-ALD-003" not in {item["id"] for item in other["assets"]}

