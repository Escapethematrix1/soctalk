"""Tests for RH Sentry's isolated synthetic-event pipeline only."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from event_pipeline import generate_scenario, scenario_catalogue
from server import create_app

PASSWORD = "test-only-rh-sentry-2026"


@pytest.fixture
def lab(tmp_path: Path):
    path = tmp_path / "pipeline.sqlite3"
    with TestClient(create_app(path, PASSWORD)) as http:
        yield http, path


def login(http: TestClient, actor: str) -> str:
    result = http.post("/api/lab/login", json={"username": actor, "password": PASSWORD})
    assert result.status_code == 200
    return result.json()["csrfToken"]


def submit(http: TestClient, token: str | None, tenant: str, scenario: str, key: str):
    headers = {"X-CSRF-Token": token} if token else {}
    return http.post(
        f"/api/tenants/{tenant}/lab/scenarios/ingest",
        headers=headers,
        json={"scenarioId": scenario, "idempotencyKey": key},
    )


def test_fixtures_never_claim_live_data():
    catalogue = scenario_catalogue()
    assert len(catalogue) == 4
    for item in catalogue:
        events, matches = generate_scenario(item["id"], "alderwick")
        assert 1 <= len(events) <= 2
        assert all(event["source"] == "rh-sentry-synthetic-lab" for event in events)
        assert all(event["actor"].endswith(".invalid") for event in events)
        assert all(set(corr["event_offsets"]).issubset(set(range(len(events)))) for corr in matches)
    assert len(generate_scenario("ordinary-signins", "alderwick")[1]) == 0
    assert len(generate_scenario("partial-auth", "alderwick")[1]) == 0
    assert generate_scenario("impossible-travel", "alderwick")[1][0]["rule_id"] == "RHS-DET-001"
    with pytest.raises(ValueError):
        generate_scenario("not-real", "alderwick")


def test_requires_authentication_and_csrf(lab):
    http, _ = lab
    url = "/api/tenants/alderwick/lab/scenarios/ingest"
    body = {"scenarioId": "impossible-travel", "idempotencyKey": "csrf-validation-001"}
    assert http.get("/api/tenants/alderwick/lab/events").status_code == 401
    assert http.post(url, json=body).status_code == 401
    login(http, "alderwick-analyst")
    assert http.post(url, json=body).status_code == 403
    assert http.post(url, json=body, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert http.post(url, json=body, headers={
        "Origin": "https://attacker.invalid",
        "X-CSRF-Token": "wrong",
    }).status_code == 403


def test_viewer_cannot_read_training_telemetry_or_ingest(lab):
    http, _ = lab
    token = login(http, "alderwick-viewer")
    assert http.get("/api/tenants/alderwick/lab/scenarios").status_code == 403
    assert http.get("/api/tenants/alderwick/lab/events").status_code == 403
    assert http.get("/api/tenants/alderwick/lab/correlations").status_code == 403
    assert submit(http, token, "alderwick", "ordinary-signins", "viewer-denied-0001").status_code == 403


def test_analyst_can_create_and_inspect_explainable_correlation(lab):
    http, db_path = lab
    token = login(http, "alderwick-analyst")
    response = submit(http, token, "alderwick", "impossible-travel", "same-tenant-event-0001")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["replayed"] is False
    assert body["eventCount"] == 2
    assert body["correlationCount"] == 1
    events = http.get("/api/tenants/alderwick/lab/events")
    assert events.status_code == 200
    entries = events.json()["items"]
    assert len(entries) == 2
    assert {event["tenantId"] for event in entries if "tenantId" in event} == set()
    assert all(event["source"] == "rh-sentry-synthetic-lab" for event in entries)
    assert all(event["attributes"]["identity"].endswith(".invalid") for event in entries)
    correlations = http.get("/api/tenants/alderwick/lab/correlations")
    assert correlations.status_code == 200
    match = correlations.json()["items"][0]
    assert match["ruleId"] == "RHS-DET-001"
    assert match["caseId"] == "SEN-2048"
    assert set(match["eventIds"]) == {event["id"] for event in entries}
    case = http.get("/api/tenants/alderwick/incidents/SEN-2048").json()
    assert case["version"] == 1  # Correlation does not rewrite case status/evidence.
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM synthetic_events WHERE tenant_id='alderwick'").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM synthetic_correlations WHERE tenant_id='alderwick'").fetchone()[0] == 1


def test_replay_same_token_is_idempotent_and_conflict_is_denied(lab):
    http, db_path = lab
    token = login(http, "alderwick-analyst")
    first = submit(http, token, "alderwick", "encoded-powershell", "client-token-replay-00001")
    assert first.status_code == 201
    replay = submit(http, token, "alderwick", "encoded-powershell", "client-token-replay-00001")
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["batchId"] == first.json()["batchId"]
    conflict = submit(http, token, "alderwick", "ordinary-signins", "client-token-replay-00001")
    assert conflict.status_code == 409
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM synthetic_event_batches").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM synthetic_events").fetchone()[0] == 1


def test_non_matching_and_incomplete_events_do_not_generate_cases(lab):
    http, _ = lab
    token = login(http, "alderwick-analyst")
    for scenario, key in [("ordinary-signins", "ordinary-event-0001"), ("partial-auth", "missing-geo-00001")]:
        response = submit(http, token, "alderwick", scenario, key)
        assert response.status_code == 201
        assert response.json()["correlationCount"] == 0
    assert http.get("/api/tenants/alderwick/lab/correlations").json()["items"] == []
    assert http.get("/api/tenants/alderwick/incidents").json()["items"][0]["version"] == 1


def test_cross_tenant_reads_and_writes_are_denied(lab):
    http, db_path = lab
    token = login(http, "alderwick-analyst")
    assert submit(http, token, "summit", "impossible-travel", "foreign-attempt-0001").status_code == 404
    assert http.get("/api/tenants/summit/lab/events").status_code == 404
    assert http.get("/api/tenants/harbourline/lab/correlations").status_code == 404
    assert http.get("/api/tenants/summit/lab/scenarios").status_code == 404
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM synthetic_event_batches").fetchone()[0] == 0


def test_rejects_untrusted_event_payloads_and_invalid_scenarios(lab):
    http, _ = lab
    token = login(http, "alderwick-analyst")
    url = "/api/tenants/alderwick/lab/scenarios/ingest"
    headers = {"X-CSRF-Token": token}
    for payload in [
        {"scenarioId": "arbitrary", "idempotencyKey": "untrusted-case-001"},
        {"scenarioId": "ordinary-signins", "idempotencyKey": "untrusted-case-002",
         "rawLog": {"password": "should-not-save"}},
        {"scenarioId": "ordinary-signins", "idempotencyKey": "wrong token"},
        {"scenarioId": "ordinary-signins", "idempotencyKey": "short"},
        {"scenarioId": "ordinary-signins", "idempotencyKey": "untrusted-case-003",
         "endpointUrl": "https://example.invalid"},
    ]:
        assert http.post(url, json=payload, headers=headers).status_code == 422
    assert http.get("/api/tenants/alderwick/lab/events").json()["items"] == []


def test_correlation_has_no_other_tenant_case_link(lab):
    http, _ = lab
    token = login(http, "harbourline-viewer")
    assert submit(http, token, "harbourline", "impossible-travel", "other-company-0001").status_code == 403
    # This tenant currently has no fictional analyst account. Pure fixture
    # correlation must therefore remain explicitly unlinked.
    _, matches = generate_scenario("impossible-travel", "harbourline")
    assert matches[0]["case_id"] is None


def test_persistence_across_restarting_local_api(lab):
    http, db_path = lab
    token = login(http, "alderwick-analyst")
    assert submit(http, token, "alderwick", "encoded-powershell", "persistent-event-0001").status_code == 201
    with TestClient(create_app(db_path, PASSWORD)) as restarted:
        login(restarted, "alderwick-analyst")
        assert len(restarted.get("/api/tenants/alderwick/lab/events").json()["items"]) == 1
        entries = restarted.get("/api/tenants/alderwick/lab/correlations").json()["items"]
        assert len(entries) == 1
        assert entries[0]["caseId"] == "SEN-2047"
