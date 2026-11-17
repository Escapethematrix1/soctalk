"""Synthetic Detection Engineering rules, provenance, tenancy and review tests."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from detection_lab import evaluate, validate_threshold
from server import create_app

PW = "test-only-detection-password-2026"


@pytest.fixture
def lab(tmp_path: Path):
    path = tmp_path / "detections.sqlite3"
    with TestClient(create_app(path, PW)) as client:
        yield client, path


def login(client, user="alderwick-analyst"):
    response = client.post("/api/lab/login", json={"username": user, "password": PW})
    assert response.status_code == 200
    return response.json()["csrfToken"]


def base(tenant="alderwick"):
    return f"/api/tenants/{tenant}/lab"


def ingest(client, csrf, scenario="impossible-travel", tenant="alderwick", key="detections-test-batch-001"):
    response = client.post(base(tenant) + "/scenarios/ingest", headers={"X-CSRF-Token": csrf},
        json={"scenarioId": scenario, "idempotencyKey": key})
    assert response.status_code == 201, response.text
    return response.json()["batchId"]


def run(client, csrf, batch_id, rule="RHS-DET-001", version=1,
        key="detections-rule-test-001", tenant="alderwick"):
    return client.post(base(tenant) + f"/detection-rules/{rule}/test",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": version, "batchId": batch_id, "idempotencyKey": key})


def test_detection_predicates_fail_closed_on_incomplete_input():
    validate_threshold("identity_travel", 500)
    with pytest.raises(ValueError):
        validate_threshold("identity_travel", 10)
    with pytest.raises(ValueError):
        validate_threshold("wazuh_ssh_burst", 1)
    with pytest.raises(ValueError):
        validate_threshold("encoded_powershell", 2)
    assert evaluate("identity_travel", 500, []) == []
    assert evaluate("encoded_powershell", 1, []) == []
    assert evaluate("wazuh_ssh_burst", 3, []) == []


def test_rules_are_seeded_per_tenant_without_clobbering_existing_state(lab):
    client, path = lab
    login(client)
    response = client.get(base() + "/detection-rules")
    assert response.status_code == 200
    items = response.json()["items"]
    assert {r["strategy"] for r in items} == {
        "identity_travel", "encoded_powershell", "wazuh_ssh_burst"}
    assert len(items) == 3
    assert all(r["status"] == "draft" and r["liveDetection"] is False for r in items)
    assert client.get(base("summit") + "/detection-rules").status_code == 404
    with TestClient(create_app(path, PW)) as reopened:
        login(reopened)
        again = reopened.get(base() + "/detection-rules").json()["items"]
        assert len(again) == 3


def test_viewer_and_unauthenticated_cannot_access_detection_records(lab):
    client, _ = lab
    assert client.get(base() + "/detection-rules").status_code == 401
    token = login(client, "alderwick-viewer")
    for path in ["/detection-templates", "/detection-rules", "/event-batches",
                 "/detection-runs", "/detection-findings"]:
        assert client.get(base() + path).status_code == 403
    denied = client.post(base() + "/detection-rules", headers={"X-CSRF-Token": token},
        json={"strategy":"identity_travel", "title":"My test rule", "description":"Fictional test condition",
              "threshold":500})
    assert denied.status_code == 403


def test_rule_create_update_and_history_are_versioned(lab):
    client, path = lab
    csrf = login(client)
    rule = client.post(base() + "/detection-rules",
        headers={"X-CSRF-Token": csrf},
        json={"strategy":"identity_travel","title":"Fictional travel rule",
              "description":"Verify training identity sign-in travel patterns","threshold":600})
    assert rule.status_code == 201, rule.text
    item = rule.json()
    assert item["status"] == "draft"
    assert item["version"] == 1
    assert item["threshold"] == 600
    changed = client.patch(base() + f"/detection-rules/{item['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "threshold":700, "status":"test_enabled"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2
    assert changed.json()["threshold"] == 700
    assert client.patch(base() + f"/detection-rules/{item['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion":1,"status":"disabled"}).status_code == 409
    history = client.get(base() + f"/detection-rules/{item['id']}/history")
    assert history.status_code == 200
    assert [h["action"] for h in history.json()["items"]] == ["updated", "created"]
    with TestClient(create_app(path, PW)) as restart:
        login(restart)
        persisted = next(r for r in restart.get(base() + "/detection-rules").json()["items"]
            if r["id"] == item["id"])
        assert persisted["version"] == 2
        assert persisted["status"] == "test_enabled"


def test_synced_batches_cause_explainable_matched_and_unmatched_results(lab):
    client, path = lab
    csrf = login(client)
    suspicious = ingest(client, csrf)
    normal = ingest(client, csrf, scenario="ordinary-signins", key="detections-normal-batch-001")
    positive = run(client, csrf, suspicious)
    assert positive.status_code == 201, positive.text
    match = positive.json()
    assert match["outcome"] == "matched"
    assert match["eventCount"] == 2
    assert len(match["matchedEventIds"]) == 2
    assert match["liveDetection"] is False
    assert match["ruleVersion"] == 1
    negative = run(client, csrf, normal, key="detections-rule-test-002")
    assert negative.status_code == 201, negative.text
    assert negative.json()["outcome"] == "not_matched"
    assert negative.json()["matchedEventIds"] == []
    findings = client.get(base() + "/detection-findings").json()["items"]
    assert len(findings) == 1
    assert findings[0]["runId"] == match["id"]
    assert findings[0]["disposition"] == "unreviewed"
    assert set(findings[0]["matchedEventIds"]) == set(match["matchedEventIds"])
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 6
        assert db.execute("SELECT COUNT(*) FROM detection_test_runs").fetchone()[0] == 2


def test_wazuh_and_powershell_strategies_match_correct_only(lab):
    client, _ = lab
    token = login(client)
    windows = ingest(client, token, "encoded-powershell", key="detections-powershell-batch-001")
    ssh = ingest(client, token, "wazuh-ssh-burst", key="detections-ssh-batch-0001")
    single = ingest(client, token, "wazuh-ssh-benign", key="detections-ssh-single-0001")
    p = run(client, token, windows, "RHS-DET-002", key="detections-ps-rule-0001")
    assert p.status_code == 201
    assert len(p.json()["matchedEventIds"]) == 1
    w = run(client, token, ssh, "RHS-WAZ-SYN-001", key="detections-ssh-rule-0001")
    assert w.status_code == 201, w.text
    assert len(w.json()["matchedEventIds"]) == 3
    no_match = run(client, token, single, "RHS-WAZ-SYN-001", key="detections-ssh-rule-0002")
    assert no_match.status_code == 201
    assert no_match.json()["outcome"] == "not_matched"


def test_idempotency_keys_replay_but_refuse_other_inputs(lab):
    client, _ = lab
    token = login(client)
    one = ingest(client, token)
    two = ingest(client, token, "ordinary-signins", key="detections-other-events-001")
    first = run(client, token, one)
    assert first.status_code == 201
    replay = run(client, token, one)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["id"] == first.json()["id"]
    assert run(client, token, two).status_code == 409
    assert len(client.get(base() + "/detection-runs").json()["items"]) == 1


def test_cross_tenant_batch_and_rules_cannot_be_tested(lab):
    client, path = lab
    token = login(client)
    batch = ingest(client, token)
    assert run(client, token, batch, tenant="summit").status_code == 404
    assert client.patch(base("summit") + "/detection-rules/RHS-DET-001",
        headers={"X-CSRF-Token":token},
        json={"expectedVersion":1,"status":"disabled"}).status_code == 404
    assert client.get(base("summit") + "/detection-findings").status_code == 404
    wrong = run(client, token, 99999)
    assert wrong.status_code == 404
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM detection_test_runs").fetchone()[0] == 0


def test_rejects_missing_csrf_and_arbitrary_executable_rules(lab):
    client, _ = lab
    token = login(client)
    path = base() + "/detection-rules"
    for payload in [
        {"strategy":"run_python","title":"Arbitrary rule", "description":"Run an attacker command", "threshold":1},
        {"strategy":"identity_travel","title":"Custom rule", "description":"Test arbitrary code", "threshold":1},
        {"strategy":"encoded_powershell","title":"Custom rule", "description":"Safe rule test", "threshold":2},
        {"strategy":"identity_travel","title":"Custom rule", "description":"Safe rule test", "threshold":500,
         "eval":"exec('something')"},
    ]:
        assert client.post(path,headers={"X-CSRF-Token":token},json=payload).status_code == 422
    assert client.post(path,json={"strategy":"identity_travel","title":"My detection",
        "description":"Safe test rule description","threshold":500}).status_code == 403
    assert client.get(path).json()["items"]


def test_false_positive_review_is_versioned_and_audited(lab):
    client, path = lab
    csrf = login(client)
    batch = ingest(client, csrf)
    run_id = run(client, csrf, batch).json()["id"]
    findings = client.get(base() + "/detection-findings").json()["items"]
    assert len(findings) == 1
    finding_id = findings[0]["id"]
    review_url = base() + f"/detection-findings/{finding_id}/review"
    missing = client.post(review_url,json={"expectedVersion":1,"disposition":"false_positive",
        "reason":"Known expected login during training."})
    assert missing.status_code == 403
    result = client.post(review_url,headers={"X-CSRF-Token":csrf},
        json={"expectedVersion":1,"disposition":"false_positive",
              "reason":"Expected fictional sign-in for this training case."})
    assert result.status_code == 200, result.text
    assert result.json()["version"] == 2
    assert client.post(review_url,headers={"X-CSRF-Token":csrf},
        json={"expectedVersion":1,"disposition":"needs_investigation",
              "reason":"Potentially relevant synthetic activity."}).status_code == 409
    events = client.get(base() + f"/detection-findings/{finding_id}/reviews").json()["items"]
    assert len(events) == 1
    assert events[0]["disposition"] == "false_positive"
    assert "Expected fictional" in events[0]["reason"]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 6
        assert db.execute("SELECT COUNT(*) FROM detection_findings").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM audit_events WHERE operation='detections:review'").fetchone()[0] == 1


def test_disabled_rule_cannot_run_and_does_not_mutate_history(lab):
    client, path = lab
    csrf = login(client)
    batch = ingest(client, csrf)
    changed = client.patch(base() + "/detection-rules/RHS-DET-001",
        headers={"X-CSRF-Token":csrf},json={"expectedVersion":1,"status":"disabled"})
    assert changed.status_code == 200
    assert run(client,csrf,batch,version=2).status_code == 409
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM detection_test_runs").fetchone()[0] == 0


def test_detection_run_and_review_survive_restart_with_snapshot(lab):
    client, path = lab
    csrf = login(client)
    batch = ingest(client, csrf)
    tested = run(client, csrf, batch).json()
    finding = client.get(base() + "/detection-findings").json()["items"][0]
    review = client.post(base() + f"/detection-findings/{finding['id']}/review",
        headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "disposition": "needs_investigation",
              "reason": "Fictional behaviour deserves analyst examination."})
    assert review.status_code == 200, review.text
    changed = client.patch(base() + "/detection-rules/RHS-DET-001",
        headers={"X-CSRF-Token":csrf},
        json={"expectedVersion":1,"threshold":1200})
    assert changed.status_code == 200, changed.text
    with TestClient(create_app(path, PW)) as restored:
        login(restored)
        runs = restored.get(base() + "/detection-runs").json()["items"]
        assert len(runs) == 1
        assert runs[0]["id"] == tested["id"]
        assert runs[0]["ruleVersion"] == 1
        assert runs[0]["threshold"] == 500
        assert len(runs[0]["matchedEventIds"]) == 2
        findings = restored.get(base() + "/detection-findings").json()["items"]
        assert len(findings) == 1
        assert findings[0]["disposition"] == "needs_investigation"
        assert findings[0]["version"] == 2
        reviewed = restored.get(base() + f"/detection-findings/{finding['id']}/reviews").json()["items"]
        assert len(reviewed) == 1
        assert reviewed[0]["reason"].startswith("Fictional behaviour")
        rule = next(x for x in restored.get(base() + "/detection-rules").json()["items"]
                    if x["id"] == "RHS-DET-001")
        assert rule["version"] == 2
        assert rule["threshold"] == 1200


def test_database_disallows_cross_tenant_finding_review_links(lab):
    client, path = lab
    csrf = login(client)
    batch = ingest(client, csrf)
    run(client, csrf, batch)
    finding = client.get(base() + "/detection-findings").json()["items"][0]
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO detection_finding_reviews "
                "(tenant_id,finding_id,actor,disposition,reason,version,reviewed_at)"
                "VALUES (?,?,?,?,?,?,?)",
                ("summit", finding["id"], "lab-auditor", "false_positive",
                 "Cross tenant direct insertion must fail", 2, "2026-11-17T00:00:00+00:00")
            )
