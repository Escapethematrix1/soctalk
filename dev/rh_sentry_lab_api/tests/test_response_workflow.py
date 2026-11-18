"""RH Sentry response proposal approval tests. Fictional data and dry-run only."""
from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
from server import create_app

PASSWORD = "test-only-responders-password-2026"

@pytest.fixture
def lab(tmp_path: Path):
    db = tmp_path / "responses.sqlite3"
    with TestClient(create_app(db, PASSWORD)) as client:
        yield client, db

def login(client, name="alderwick-analyst"):
    response = client.post("/api/lab/login", json={"username":name,"password":PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["csrfToken"]

def base(tenant="alderwick"):
    return f"/api/tenants/{tenant}/lab/response-requests"

def propose(client, csrf, tenant="alderwick", incident="SEN-2048", key="response-proposal-0001",
            playbook="identity_review", reason="Review this fictional sign-in evidence and verify account owner."):
    return client.post(base(tenant), headers={"X-CSRF-Token":csrf},
        json={"incidentId":incident,"playbookId":playbook,
              "idempotencyKey":key,"reason":reason})

def decision(client, csrf, req_id, value="approve_dry_run", version=1, tenant="alderwick"):
    return client.post(base(tenant)+f"/{req_id}/decision",
      headers={"X-CSRF-Token":csrf},
      json={"expectedVersion":version,"decision":value,
            "reason":"Independent review of synthetic investigation and business impact."})

def simulate(client, csrf, req_id, version=2, tenant="alderwick"):
    return client.post(base(tenant)+f"/{req_id}/simulate",
      headers={"X-CSRF-Token":csrf},json={"expectedVersion":version})

def test_catalogue_requires_analyst_and_does_not_expose_executors(lab):
    client, _ = lab
    assert client.get("/api/tenants/alderwick/lab/response-playbooks").status_code == 401
    login(client)
    response=client.get("/api/tenants/alderwick/lab/response-playbooks")
    assert response.status_code==200
    assert {x["id"] for x in response.json()["items"]} == {
      "identity_review","process_review","session_revocation","endpoint_isolation"}
    assert all(x["dryRunOnly"] and not x["executable"] for x in response.json()["items"])
    assert client.get("/api/tenants/summit/lab/response-playbooks").status_code == 404
    login(client,"alderwick-viewer")
    assert client.get("/api/tenants/alderwick/lab/response-playbooks").status_code == 403

def test_readonly_customer_is_denied_and_cross_tenant_proposals_fail(lab):
    client, db = lab
    csrf=login(client,"alderwick-viewer")
    assert client.get(base()).status_code==403
    assert propose(client,csrf).status_code==403
    csrf=login(client)
    assert propose(client,csrf,tenant="summit").status_code==404
    assert propose(client,csrf,incident="SEN-2046").status_code==404
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM response_requests").fetchone()[0]==0

def test_propose_idempotent_and_no_implicit_execution(lab):
    client, db=lab
    csrf=login(client)
    first=propose(client,csrf)
    assert first.status_code==201,first.text
    record=first.json()
    assert record["status"]=="pending" and record["version"]==1
    assert record["liveExecution"] is False and not record["dryRunRecorded"]
    duplicate=propose(client,csrf)
    assert duplicate.status_code==200
    assert duplicate.json()["replayed"] is True
    assert duplicate.json()["id"]==record["id"]
    collision=propose(client,csrf,reason="Different fictional rationale for another response.")
    assert collision.status_code==409
    assert client.get(base()).json()["items"][0]["id"]==record["id"]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM response_requests").fetchone()[0]==1
        assert conn.execute("SELECT COUNT(*) FROM response_dry_run_receipts").fetchone()[0]==0

def test_separation_of_duties_lead_approval_and_dry_run_receipt(lab):
    client,db=lab
    analyst_csrf=login(client)
    proposed=propose(client,analyst_csrf,playbook="endpoint_isolation").json()
    rid=proposed["id"]
    assert simulate(client,analyst_csrf,rid,version=1).status_code==403
    assert decision(client,analyst_csrf,rid).status_code==403
    lead_csrf=login(client,"alderwick-lead")
    assert simulate(client,lead_csrf,rid,version=1).status_code==409
    decided=decision(client,lead_csrf,rid)
    assert decided.status_code==200,decided.text
    assert decided.json()["status"]=="approved_dry_run"
    assert decided.json()["version"]==2
    assert decision(client,lead_csrf,rid,version=1).status_code==409
    receipt=simulate(client,lead_csrf,rid)
    assert receipt.status_code==200,receipt.text
    assert receipt.json()["externalActions"]==0
    assert receipt.json()["liveExecution"] is False
    assert "No external systems contacted" in receipt.json()["result"]
    replay=simulate(client,lead_csrf,rid)
    assert replay.json()["receiptId"]==receipt.json()["receiptId"]
    analyst_again=login(client,"alderwick-analyst")
    replay_original=propose(client,analyst_again,playbook="endpoint_isolation")
    assert replay_original.status_code==200, replay_original.text
    assert replay_original.json()["dryRunRecorded"] is True
    assert replay_original.json()["status"]=="approved_dry_run"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM response_dry_run_receipts").fetchone()[0]==1
        assert conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]==6
    history=client.get(base()+f"/{rid}/history")
    assert [x["action"] for x in history.json()["items"]]==[
      "proposed","approved_dry_run","dry_run_recorded"]
    assert client.get(base()).json()["items"][0]["dryRunRecorded"] is True

def test_lead_cannot_self_approve(lab):
    client,_=lab
    csrf=login(client,"alderwick-lead")
    new=propose(client,csrf,key="lead-proposal-0002").json()
    assert decision(client,csrf,new["id"]).status_code==403
    assert client.get(base()).json()["items"][0]["status"]=="pending"

def test_rejection_is_terminal_and_never_simulatable(lab):
    client,_=lab
    analyst=login(client)
    rid=propose(client,analyst,key="reject-proposal-0001").json()["id"]
    lead=login(client,"alderwick-lead")
    assert decision(client,lead,rid,value="reject").status_code==200
    assert simulate(client,lead,rid).status_code==409
    assert decision(client,lead,rid,version=2).status_code==409
    assert client.get(base()).json()["items"][0]["status"]=="rejected"

def test_csrf_and_untrusted_action_fields_rejected(lab):
    client,_=lab
    csrf=login(client)
    assert client.post(base(),json={"incidentId":"SEN-2048","playbookId":"identity_review",
        "reason":"Review this fictional identity sign-in evidence.",
        "idempotencyKey":"token-no-csrf-0001"}).status_code==403
    assert client.post(base(),headers={"X-CSRF-Token":csrf},
        json={"incidentId":"SEN-2048","playbookId":"execute_command",
              "reason":"Execute arbitrary response command on customer host.",
              "idempotencyKey":"invalid-playbook-0001"}).status_code==422
    assert client.post(base(),headers={"X-CSRF-Token":csrf},
        json={"incidentId":"SEN-2048","playbookId":"identity_review",
              "reason":"Review this fictional identity sign-in evidence.",
              "idempotencyKey":"extra-field-token-0001","command":"rm -rf /"}).status_code==422
    assert client.post(base(),headers={"X-CSRF-Token":csrf,"Origin":"https://untrusted.invalid"},
        json={"incidentId":"SEN-2048","playbookId":"identity_review",
              "reason":"Review this fictional identity sign-in evidence.",
              "idempotencyKey":"foreign-origin-token-0001"}).status_code==403

def test_persistence_across_restart_does_not_reset_approval(lab):
    client,db=lab
    analyst=login(client)
    rid=propose(client,analyst,key="persist-proposal-0001").json()["id"]
    lead=login(client,"alderwick-lead")
    assert decision(client,lead,rid).status_code==200
    assert simulate(client,lead,rid).status_code==200
    with TestClient(create_app(db,PASSWORD)) as restarted:
        login(restarted,"alderwick-lead")
        item=restarted.get(base()).json()["items"][0]
        assert item["id"]==rid
        assert item["dryRunRecorded"] is True
        assert item["status"]=="approved_dry_run"
        assert len(restarted.get(base()+f"/{rid}/history").json()["items"])==3
