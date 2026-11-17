"""RH Sentry fictional asset inventory: tenancy, mutations and incident linkage."""
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from server import create_app

PASSWORD = "asset-lab-testing-password-2026"


@pytest.fixture
def lab(tmp_path: Path):
    path = tmp_path / "assets.sqlite3"
    with TestClient(create_app(path, PASSWORD)) as client:
        yield client, path


def login(client: TestClient, actor: str) -> str:
    result = client.post("/api/lab/login", json={"username": actor, "password": PASSWORD})
    assert result.status_code == 200, result.text
    return result.json()["csrfToken"]


def asset_path(tenant="alderwick", asset="AST-ALD-001"):
    return f"/api/tenants/{tenant}/assets/{asset}"


def create(client, csrf, tenant="alderwick", **overrides):
    body = {
        "displayName": "TRAINING-WIN-42",
        "assetType": "endpoint",
        "environment": "workstation",
        "owner": "IT team",
        "criticality": "medium",
        "lifecycle": "active",
        **overrides,
    }
    return client.post(f"/api/tenants/{tenant}/assets",
                       headers={"X-CSRF-Token": csrf}, json=body)


def update(client, csrf, tenant="alderwick", asset="AST-ALD-001", **changes):
    return client.patch(asset_path(tenant, asset),
                        headers={"X-CSRF-Token": csrf} if csrf is not None else {}, json=changes)


def test_default_assets_are_fictional_not_connected_and_customer_scoped(lab):
    client, _ = lab
    assert client.get("/api/tenants/alderwick/assets").status_code == 401
    login(client, "alderwick-viewer")
    result = client.get("/api/tenants/alderwick/assets")
    assert result.status_code == 200
    data = result.json()
    assert data["source"] == "local-sqlite-fictional"
    assert data["liveSensors"] == 0
    assert data["tenantId"] == "alderwick"
    assert len(data["items"]) == 4
    assert all(x["tenantId"] == "alderwick" for x in data["items"])
    assert all(x["monitoringState"] == "not_connected" and x["lastSeen"] is None for x in data["items"])
    assert client.get("/api/tenants/summit/assets").status_code == 404
    assert client.get("/api/tenants/summit/assets/AST-SUM-001").status_code == 404
    assert client.get(asset_path()).json()["id"] == "AST-ALD-001"


def test_viewer_cannot_create_update_link_unlink_or_read_history(lab):
    client, _ = lab
    csrf = login(client, "alderwick-viewer")
    assert create(client, csrf).status_code == 403
    assert update(client, csrf, expectedVersion=1, criticality="critical").status_code == 403
    link_url = asset_path() + "/incidents"
    assert client.post(link_url, headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "incidentId": "SEN-2048"}).status_code == 403
    assert client.request("DELETE", link_url + "/SEN-2047", headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1}).status_code == 403
    assert client.get(asset_path() + "/history").status_code == 403
    allowed = client.get(asset_path() + "/incidents")
    assert allowed.status_code == 200
    assert {x["id"] for x in allowed.json()["items"]} == {"SEN-2047"}


def test_analyst_create_and_update_survives_restart(lab):
    client, db = lab
    csrf = login(client, "alderwick-analyst")
    response = create(client, csrf)
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["tenantId"] == "alderwick"
    assert item["version"] == 1
    assert item["monitoringState"] == "not_connected"
    assert item["lastSeen"] is None
    asset_id = item["id"]
    patched = update(client, csrf, asset=asset_id, expectedVersion=1,
                     criticality="critical", lifecycle="maintenance", owner=None)
    assert patched.status_code == 200, patched.text
    assert patched.json()["version"] == 2
    assert patched.json()["criticality"] == "critical"
    assert patched.json()["lifecycle"] == "maintenance"
    assert patched.json()["owner"] is None
    assert patched.json()["monitoringState"] == "not_connected"
    history = client.get(asset_path(asset=asset_id) + "/history").json()["items"]
    assert [e["action"] for e in history] == ["asset_updated", "asset_created"]
    assert [e["version"] for e in history] == [2, 1]
    with TestClient(create_app(db, PASSWORD)) as restarted:
        login(restarted, "alderwick-analyst")
        result = restarted.get(asset_path(asset=asset_id)).json()
        assert result["version"] == 2
        assert result["owner"] is None
        assert result["monitoringState"] == "not_connected"


def test_cross_tenant_operations_are_denied_and_restricted_links(lab):
    client, db = lab
    csrf = login(client, "alderwick-analyst")
    assert create(client, csrf, "summit").status_code == 404
    assert update(client, csrf, "summit", "AST-SUM-001",
                  expectedVersion=1, criticality="high").status_code == 404
    assert client.get(asset_path("summit", "AST-SUM-001") + "/incidents").status_code == 404
    assert client.get(asset_path("summit", "AST-SUM-001") + "/history").status_code == 404
    url = asset_path() + "/incidents"
    foreign = client.post(url, headers={"X-CSRF-Token": csrf},
                          json={"expectedVersion": 1, "incidentId": "SEN-2046"})
    assert foreign.status_code == 404
    with sqlite3.connect(db) as handle:
        assert handle.execute("SELECT COUNT(*) FROM asset_incident_links WHERE tenant_id='alderwick'").fetchone()[0] == 2
        assert handle.execute("SELECT COUNT(*) FROM assets WHERE tenant_id='summit'").fetchone()[0] == 2


def test_incident_links_are_versioned_and_reversible(lab):
    client, db_path = lab
    csrf = login(client, "alderwick-analyst")
    url = asset_path(asset="AST-ALD-003") + "/incidents"
    entry = client.post(url, headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1, "incidentId": "SEN-2048"})
    assert entry.status_code == 201, entry.text
    assert entry.json()["version"] == 2
    linked = client.get(url).json()["items"]
    assert len(linked) == 1
    assert linked[0]["id"] == "SEN-2048"
    assert client.post(url, headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 2, "incidentId": "SEN-2048"}).status_code == 409
    assert client.request("DELETE", url + "/SEN-2048", headers={"X-CSRF-Token": csrf},
        json={"expectedVersion": 1}).status_code == 409
    removed = client.request("DELETE", url + "/SEN-2048", headers={"X-CSRF-Token": csrf},
                            json={"expectedVersion": 2})
    assert removed.status_code == 200, removed.text
    assert removed.json()["version"] == 3
    assert client.get(url).json()["items"] == []
    history = client.get(asset_path(asset="AST-ALD-003") + "/history").json()["items"]
    assert [x["action"] for x in history[:2]] == ["incident_unlinked", "incident_linked"]
    with TestClient(create_app(db_path, PASSWORD)) as reopened:
        login(reopened, "alderwick-analyst")
        assert reopened.get(url).json()["items"] == []
        assert reopened.get(asset_path(asset="AST-ALD-003")).json()["version"] == 3


def test_csrf_and_origin_are_mandatory_for_all_asset_writes(lab):
    client, _ = lab
    assert client.post("/api/tenants/alderwick/assets", json={
        "displayName": "LAB-TEST", "assetType": "server", "environment": "testing"}).status_code == 401
    csrf = login(client, "alderwick-analyst")
    assert client.post("/api/tenants/alderwick/assets", json={
        "displayName": "LAB-TEST", "assetType": "server", "environment": "testing"}).status_code == 403
    assert update(client, None, expectedVersion=1, criticality="low").status_code == 403
    assert client.request("DELETE", asset_path() + "/incidents/SEN-2047",
                         json={"expectedVersion": 1}).status_code == 403
    foreign = client.patch(asset_path(), headers={
        "X-CSRF-Token": csrf, "Origin": "https://untrusted.invalid"},
        json={"expectedVersion": 1, "criticality": "low"})
    assert foreign.status_code == 403


@pytest.mark.parametrize("extra", [
    {"telemetryUrl": "https://untrusted.invalid"},
    {"monitoringState": "connected"},
    {"lastSeen": "2026-11-17"},
    {"agentToken": "fake-token"},
    {"command": "whoami"},
])
def test_asset_registration_cannot_fake_monitoring_or_execute(extra, lab):
    client, _ = lab
    csrf = login(client, "alderwick-analyst")
    result = create(client, csrf, **extra)
    assert result.status_code == 422


@pytest.mark.parametrize("extra", [
    {"assetType": "scanner"},
    {"criticality": "unknown"},
    {"displayName": "<script>alert(1)</script>"},
    {"environment": "https://untrusted.invalid"},
    {"owner": "invalid@demo.invalid"},
])
def test_asset_input_validation_rejects_untrusted_fields(extra, lab):
    client, _ = lab
    csrf = login(client, "alderwick-analyst")
    result = create(client, csrf, **extra)
    assert result.status_code == 422


def test_duplicate_names_and_stale_writes_fail(lab):
    client, _ = lab
    csrf = login(client, "alderwick-analyst")
    assert create(client, csrf, displayName="WIN-DEMO-07").status_code == 409
    assert create(client, csrf, displayName="win-demo-07").status_code == 409
    assert update(client, csrf, expectedVersion=2, criticality="critical").status_code == 409
    assert update(client, csrf, expectedVersion=1, criticality="high").status_code == 422
    assert update(client, csrf, expectedVersion=1, criticality="high",
                  monitoringState="connected").status_code == 422
    assert client.get(asset_path()).json()["version"] == 1


def test_seeding_is_non_destructive_and_does_not_duplicate_links(lab):
    client, path = lab
    login(client, "alderwick-analyst")
    assert len(client.get("/api/tenants/alderwick/assets").json()["items"]) == 4
    assert len(client.get(asset_path() + "/incidents").json()["items"]) == 1
    with TestClient(create_app(path, PASSWORD)) as reopened:
        login(reopened, "alderwick-analyst")
        assert len(reopened.get("/api/tenants/alderwick/assets").json()["items"]) == 4
        assert len(reopened.get(asset_path() + "/incidents").json()["items"]) == 1


def test_overview_maintains_zero_live_coverage_after_asset_registration(lab):
    client, _ = lab
    csrf = login(client, "alderwick-analyst")
    assert create(client, csrf).status_code == 201
    overview = client.get("/api/tenants/alderwick/lab/overview").json()
    assert overview["liveSensors"] == 0
    assert overview["liveCoveragePercent"] == 0
    assert overview["assetSummary"]["registered"] == 5
    assert overview["assetSummary"]["active"] == 4
    assert overview["assetSummary"]["connected"] == 0


def test_unlinking_seeded_relation_stays_removed_after_restart(lab):
    client, path = lab
    csrf = login(client, "alderwick-analyst")
    linked_path = asset_path(asset="AST-ALD-001") + "/incidents"
    assert len(client.get(linked_path).json()["items"]) == 1
    unlinked = client.request("DELETE", linked_path + "/SEN-2047",
                              headers={"X-CSRF-Token": csrf},
                              json={"expectedVersion": 1})
    assert unlinked.status_code == 200, unlinked.text
    with TestClient(create_app(path, PASSWORD)) as reopened:
        login(reopened, "alderwick-analyst")
        assert reopened.get(linked_path).json()["items"] == []
        assert reopened.get(asset_path(asset="AST-ALD-001")).json()["version"] == 2
