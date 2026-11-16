"""Isolated security and persistence tests for the RH Sentry incident lab."""
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from server import create_app

SECRET = "synthetic-test-only-password-2026"


@pytest.fixture
def lab(tmp_path: Path):
    db_path = tmp_path / "case-lab.sqlite3"
    with TestClient(create_app(db_path, SECRET)) as http:
        yield http, db_path


def login(http: TestClient, username: str) -> str:
    response = http.post("/api/lab/login", json={"username": username, "password": SECRET})
    assert response.status_code == 200, response.text
    return response.json()["csrfToken"]


def update(http: TestClient, token: str | None, tenant="alderwick", incident="SEN-2047", **fields):
    headers = {"X-CSRF-Token": token} if token is not None else {}
    return http.patch(f"/api/tenants/{tenant}/incidents/{incident}", headers=headers,
                      json=fields)


def note(http: TestClient, token: str, tenant="alderwick", incident="SEN-2047", **fields):
    return http.post(f"/api/tenants/{tenant}/incidents/{incident}/evidence",
                     headers={"X-CSRF-Token": token}, json=fields)


def test_initial_fixture_has_versions_and_can_upgrade_existing_database(tmp_path):
    db_path = tmp_path / "old-version.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE tenants(id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        db.execute("INSERT INTO tenants VALUES ('alderwick', 'Alderwick Logistics')")
        db.execute("CREATE TABLE incidents(id TEXT NOT NULL, tenant_id TEXT NOT NULL, "
                   "title TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL, "
                   "PRIMARY KEY(id,tenant_id))")
        db.execute("INSERT INTO incidents VALUES "
                   "('SEN-CUSTOM','alderwick','Pre-existing test case','high','triage')")
    with TestClient(create_app(db_path, SECRET)) as http:
        login(http, "alderwick-analyst")
        incident = http.get("/api/tenants/alderwick/incidents/SEN-CUSTOM")
        assert incident.status_code == 200
        assert incident.json()["version"] == 1
        assert incident.json()["assignedTo"] is None
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM incidents WHERE id='SEN-CUSTOM'").fetchone()[0] == 1


def test_write_requires_auth_csrf_and_analyst_role(lab):
    http, _ = lab
    path = "/api/tenants/alderwick/incidents/SEN-2047"
    assert http.patch(path, json={"expectedVersion": 1, "status": "investigating"}).status_code == 401
    login(http, "alderwick-viewer")
    assert update(http, None, expectedVersion=1, status="investigating").status_code == 403
    viewer_csrf = login(http, "alderwick-viewer")
    assert update(http, viewer_csrf, expectedVersion=1, status="investigating").status_code == 403
    assert note(http, viewer_csrf, expectedVersion=1, note="Example viewer note.").status_code == 403
    assert http.get(path + "/evidence").status_code == 403
    assert http.get(path + "/history").status_code == 403
    assert http.get("/api/tenants/alderwick/analysts").status_code == 403
    assert http.get(path).json()["version"] == 1


def test_analyst_is_scoped_for_reads_writes_and_assignment_catalogue(lab):
    http, _ = lab
    csrf = login(http, "alderwick-analyst")
    assert update(http, csrf, tenant="summit", incident="SEN-2046",
                  expectedVersion=1, status="investigating").status_code == 404
    assert note(http, csrf, tenant="harbourline", incident="SEN-2045",
                expectedVersion=1, note="This would be cross-tenant evidence.").status_code == 404
    assert http.get("/api/tenants/harbourline/incidents/SEN-2045/history").status_code == 404
    assert http.get("/api/tenants/summit/incidents/SEN-2046/evidence").status_code == 404
    assert http.get("/api/tenants/summit/analysts").status_code == 404
    analysts = http.get("/api/tenants/alderwick/analysts")
    assert analysts.status_code == 200
    assert {x["username"] for x in analysts.json()["items"]} == {"alderwick-analyst", "alderwick-lead"}


def test_updates_status_and_assignment_atomically_and_persists(lab):
    http, db = lab
    csrf = login(http, "alderwick-analyst")
    path = "/api/tenants/alderwick/incidents/SEN-2047"
    result = update(http, csrf, expectedVersion=1, status="investigating", assignedTo="alderwick-lead")
    assert result.status_code == 200, result.text
    case = result.json()
    assert case["status"] == "investigating"
    assert case["version"] == 2
    assert case["assignedTo"] == "alderwick-lead"
    assert http.get(path).json()["version"] == 2
    assert any(entry["id"] == "SEN-2047" and entry["assignedTo"] == "alderwick-lead"
               for entry in http.get("/api/tenants/alderwick/incidents").json()["items"])
    timeline = http.get(path + "/history").json()["items"]
    assert timeline[0]["action"] == "case_updated"
    assert timeline[0]["actor"] == "alderwick-analyst"
    assert timeline[0]["version"] == 2
    with TestClient(create_app(db, SECRET)) as again:
        login(again, "alderwick-analyst")
        assert again.get(path).json()["assignedTo"] == "alderwick-lead"
        assert len(again.get(path + "/history").json()["items"]) == 1


def test_stale_versions_do_not_overwrite_and_invalid_transitions_fail(lab):
    http, _ = lab
    csrf = login(http, "alderwick-analyst")
    assert update(http, csrf, expectedVersion=1, status="investigating").status_code == 200
    assert update(http, csrf, expectedVersion=1, status="contained").status_code == 409
    assert update(http, csrf, expectedVersion=2, status="closed").status_code == 409
    assert update(http, csrf, expectedVersion=2, status="investigating").status_code == 422
    assert http.get("/api/tenants/alderwick/incidents/SEN-2047").json()["status"] == "investigating"


def test_assignment_validated_in_same_tenant_and_clearing_is_supported(lab):
    http, _ = lab
    csrf = login(http, "alderwick-analyst")
    assert update(http, csrf, expectedVersion=1, assignedTo="summit-viewer").status_code == 422
    assert update(http, csrf, expectedVersion=1, assignedTo="alderwick-viewer").status_code == 422
    assert update(http, csrf, expectedVersion=1, assignedTo="").status_code == 422
    assert update(http, csrf, expectedVersion=1, assignedTo="alderwick-lead").status_code == 200
    assert update(http, csrf, expectedVersion=2, assignedTo=None).json()["assignedTo"] is None
    assert http.get("/api/tenants/alderwick/incidents/SEN-2047").json()["version"] == 3


def test_evidence_note_increments_version_and_records_history(lab):
    http, db = lab
    csrf = login(http, "alderwick-analyst")
    response = note(http, csrf, expectedVersion=1,
                    note="Synthetic process ancestry requires validation.")
    assert response.status_code == 201, response.text
    assert response.json()["version"] == 2
    assert response.json()["actor"] == "alderwick-analyst"
    history = http.get("/api/tenants/alderwick/incidents/SEN-2047/history").json()["items"]
    assert history[0]["action"] == "evidence_added"
    evidence = http.get("/api/tenants/alderwick/incidents/SEN-2047/evidence").json()["items"]
    assert len(evidence) == 1
    assert evidence[0]["note"] == "Synthetic process ancestry requires validation."
    assert note(http, csrf, expectedVersion=1, note="Stale note rejected safely").status_code == 409
    with TestClient(create_app(db, SECRET)) as again:
        login(again, "alderwick-analyst")
        assert again.get("/api/tenants/alderwick/incidents/SEN-2047/evidence").json()["items"][0]["note"] == evidence[0]["note"]


@pytest.mark.parametrize("fields", [
    {"expectedVersion": 1, "note": "https://example.invalid/attachment"},
    {"expectedVersion": 1, "note": "javascript:alert(1)"},
    {"expectedVersion": 1, "note": "<img src=x onerror=alert(1)>"},
    {"expectedVersion": 1, "note": "tiny"},
    {"expectedVersion": 1, "note": "Legitimate test note.", "fileUrl": "https://example.invalid"},
    {"expectedVersion": 1, "note": "Legitimate test note.", "kind": "file"},
])
def test_no_arbitrary_evidence_url_attachment_or_markup(lab, fields):
    http, _ = lab
    csrf = login(http, "alderwick-analyst")
    assert note(http, csrf, **fields).status_code == 422
    assert http.get("/api/tenants/alderwick/incidents/SEN-2047/evidence").json()["items"] == []


def test_auditor_sees_durable_allowed_and_denied_actions_without_incident_access(lab):
    http, _ = lab
    csrf = login(http, "alderwick-analyst")
    update(http, csrf, expectedVersion=1, status="investigating")
    update(http, csrf, tenant="summit", incident="SEN-2046", expectedVersion=1, status="investigating")
    login(http, "lab-auditor")
    events = http.get("/api/lab/audit").json()["items"]
    assert any(x["operation"] == "incident:update" and x["outcome"] == "allowed" for x in events)
    assert any(x["operation"] == "incident:update" and x["outcome"] == "denied" for x in events)
    assert http.get("/api/tenants/alderwick/incidents").status_code == 404


def test_invalid_payload_cannot_sneak_in_fields_or_escape_csrf(lab):
    http, _ = lab
    csrf = login(http, "alderwick-analyst")
    path = "/api/tenants/alderwick/incidents/SEN-2047"
    assert update(http, csrf, expectedVersion=1, status="closed").status_code == 409
    assert update(http, csrf, expectedVersion=1, status="definitely-invalid").status_code == 422
    assert update(http, csrf, expectedVersion=1, status="investigating",
                  tenantId="summit").status_code == 422
    assert update(http, csrf, expectedVersion=1, assignedTo="alderwick-lead",
                  headers={"Origin": "https://foreign.invalid"}).status_code == 422  # Extra body rejected.
    denied_origin = http.patch(path, headers={"X-CSRF-Token": csrf,
                       "Origin": "https://foreign.invalid"},
                       json={"expectedVersion": 1, "status": "investigating"})
    assert denied_origin.status_code == 403
    assert http.get(path).json()["version"] == 1
