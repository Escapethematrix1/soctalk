"""Tests for the local lab; these do NOT validate production security."""
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server import COOKIE, create_app

SECRET = "temporary-local-test-secret-2026"


@pytest.fixture
def client(tmp_path: Path):
    db = tmp_path / "demo.sqlite3"
    with TestClient(create_app(db, SECRET)) as test_client:
        yield test_client, db


def login(client: TestClient, username: str):
    response = client.post("/api/lab/login", json={"username": username, "password": SECRET})
    assert response.status_code == 200
    return response.json()


def test_requires_secret_and_remains_synthetic(client):
    http, _ = client
    with pytest.raises(ValueError):
        create_app(Path("/tmp/this-db-is-never-created.sqlite3"), "weak")
    assert http.get("/api/health").json() == {
        "service": "rh-sentry-lab", "mode": "synthetic-local-only", "liveSensors": 0
    }
    assert http.get("/api/tenants").status_code == 401
    assert http.get("/api/tenants/alderwick/incidents").status_code == 401


def test_cookie_session_is_http_only_and_no_default_password(client):
    http, _ = client
    denied = http.post("/api/lab/login", json={
        "username": "alderwick-viewer", "password": "wrong-pass"
    })
    assert denied.status_code == 401
    info = login(http, "alderwick-viewer")
    assert info["user"] == "alderwick-viewer"
    cookie = http.cookies.get(COOKIE)
    assert cookie and len(cookie) > 32
    set_cookie = http.post("/api/lab/login", json={
        "username": "alderwick-viewer", "password": SECRET
    }).headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api" in set_cookie
    assert "no-store" in denied.headers.get("cache-control", "")
    assert http.get("/api/me").json()["memberships"] == [
        {"tenantId": "alderwick", "role": "customer_viewer"}
    ]


def test_own_tenant_list_and_cross_tenant_denial(client):
    http, _ = client
    login(http, "alderwick-viewer")
    assert http.get("/api/tenants").json()["items"] == [
        {"id": "alderwick", "name": "Alderwick Logistics"}
    ]
    own = http.get("/api/tenants/alderwick/incidents")
    assert own.status_code == 200
    assert {item["id"] for item in own.json()["items"]} == {"SEN-2048", "SEN-2047"}
    assert all(item["tenantId"] == "alderwick" for item in own.json()["items"])
    assert http.get("/api/tenants/summit/incidents").status_code == 404
    assert http.get("/api/tenants/harbourline/incidents/SEN-2045").status_code == 404
    assert http.get("/api/tenants/alderwick/incidents/SEN-2045").status_code == 404
    assert http.get("/api/tenants/alderwick/incidents/SEN-2048").status_code == 200


def test_auditor_metadata_does_not_imply_incident_access(client):
    http, _ = client
    login(http, "lab-auditor")
    assert len(http.get("/api/tenants").json()["items"]) == 3
    assert http.get("/api/tenants/alderwick/incidents").status_code == 404
    log = http.get("/api/lab/audit")
    assert log.status_code == 200
    assert any(
        entry["operation"] == "incidents:list" and entry["outcome"] == "denied"
        for entry in log.json()["items"]
    )


def test_logout_requires_valid_csrf_and_revokes_session(client):
    http, _ = client
    session = login(http, "alderwick-analyst")
    assert http.post("/api/lab/logout").status_code == 403
    assert http.post("/api/lab/logout", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert http.post("/api/lab/logout", headers={
        "X-CSRF-Token": session["csrfToken"]
    }).status_code == 200
    assert http.get("/api/me").status_code == 401


def test_rejects_foreign_login_origin(client):
    http, _ = client
    response = http.post(
        "/api/lab/login", json={"username": "summit-viewer", "password": SECRET},
        headers={"Origin": "https://fake-example.invalid"},
    )
    assert response.status_code == 403


def test_audit_and_incidents_survive_app_restart(client):
    http, db = client
    login(http, "summit-viewer")
    assert http.get("/api/tenants/summit/incidents").status_code == 200
    with sqlite3.connect(db) as conn:
        first_count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        first_audit = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    with TestClient(create_app(db, SECRET)) as later:
        assert later.get("/api/health").status_code == 200
        login(later, "lab-auditor")
        assert any(r["tenant_id"] == "summit" for r in later.get("/api/lab/audit").json()["items"])
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == first_count == 6
        assert conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] > first_audit
