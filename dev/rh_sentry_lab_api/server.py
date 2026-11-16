"""Local-only RH Sentry API laboratory. Fictional data; not production auth.

Run exclusively through run.py, which binds to the loopback interface.
Existing SocTalk backend and production deployments are untouched.
"""
from __future__ import annotations

import hashlib
import json
import hmac
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field
from event_pipeline import generate_scenario, scenario_catalogue

COOKIE = "rh_sentry_lab_session"
SESSION_SECONDS = 3600
ALLOWED_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")
TENANTS = [("alderwick", "Alderwick Logistics"), ("harbourline", "Harbourline Legal"),
           ("summit", "Summit Retail")]
# One temporary user password for all fictional lab identities, supplied at
# runtime via environment variable. Not acceptable for a commercial product.
ACCOUNTS = [
    ("alderwick-analyst", "soc_analyst", "alderwick"),
    ("alderwick-lead", "soc_lead", "alderwick"),
    ("alderwick-viewer", "customer_viewer", "alderwick"),
    ("harbourline-viewer", "customer_viewer", "harbourline"),
    ("summit-viewer", "customer_viewer", "summit"),
    ("lab-auditor", "platform_admin", None),
]
INCIDENTS = [
    ("SEN-2048", "alderwick", "Impossible travel authentication", "critical", "investigating"),
    ("SEN-2047", "alderwick", "Suspicious PowerShell execution", "high", "triage"),
    ("SEN-2045", "harbourline", "Unexpected mailbox forwarding rule", "high", "investigating"),
    ("SEN-2044", "harbourline", "New privileged group membership", "medium", "triage"),
    ("SEN-2046", "summit", "Multiple blocked inbound connections", "medium", "contained"),
    ("SEN-2043", "summit", "Endpoint security agent heartbeat delay", "low", "contained"),
]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@contextmanager
def connect(db_path: Path):
    db = sqlite3.connect(str(db_path), timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_database(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS identities (username TEXT PRIMARY KEY, active INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS memberships (
          username TEXT NOT NULL REFERENCES identities(username),
          tenant_id TEXT NOT NULL REFERENCES tenants(id),
          role TEXT NOT NULL, active INTEGER NOT NULL,
          PRIMARY KEY(username,tenant_id)
        );
        CREATE TABLE IF NOT EXISTS incidents (
          id TEXT NOT NULL, tenant_id TEXT NOT NULL REFERENCES tenants(id),
          title TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL,
          PRIMARY KEY(id,tenant_id)
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, csrf_hash TEXT NOT NULL,
          username TEXT NOT NULL REFERENCES identities(username), expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL,
          tenant_id TEXT, operation TEXT NOT NULL, outcome TEXT NOT NULL,
          target TEXT, occurred_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS incidents_tenant_idx ON incidents(tenant_id);
        CREATE TABLE IF NOT EXISTS incident_evidence (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tenant_id TEXT NOT NULL,
          incident_id TEXT NOT NULL,
          actor TEXT NOT NULL,
          kind TEXT NOT NULL CHECK(kind = 'analyst_note'),
          note TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(incident_id,tenant_id) REFERENCES incidents(id,tenant_id)
        );
        CREATE TABLE IF NOT EXISTS incident_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tenant_id TEXT NOT NULL,
          incident_id TEXT NOT NULL,
          actor TEXT NOT NULL,
          action TEXT NOT NULL,
          detail TEXT NOT NULL,
          version INTEGER NOT NULL,
          occurred_at TEXT NOT NULL,
          FOREIGN KEY(incident_id,tenant_id) REFERENCES incidents(id,tenant_id)
        );
        CREATE INDEX IF NOT EXISTS evidence_tenant_incident ON incident_evidence(tenant_id,incident_id);
        CREATE INDEX IF NOT EXISTS history_tenant_incident ON incident_history(tenant_id,incident_id);
        CREATE TABLE IF NOT EXISTS synthetic_event_batches (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tenant_id TEXT NOT NULL REFERENCES tenants(id),
          idempotency_key TEXT NOT NULL,
          scenario_id TEXT NOT NULL,
          submitted_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(tenant_id,idempotency_key)
        );
        CREATE TABLE IF NOT EXISTS synthetic_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          batch_id INTEGER NOT NULL REFERENCES synthetic_event_batches(id),
          tenant_id TEXT NOT NULL REFERENCES tenants(id),
          event_type TEXT NOT NULL,
          occurred_at TEXT NOT NULL,
          source TEXT NOT NULL,
          actor TEXT NOT NULL,
          host TEXT NOT NULL,
          description TEXT NOT NULL,
          attributes_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS synthetic_events_tenant_idx ON synthetic_events(tenant_id,id DESC);
        CREATE TABLE IF NOT EXISTS synthetic_correlations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          batch_id INTEGER NOT NULL REFERENCES synthetic_event_batches(id),
          tenant_id TEXT NOT NULL REFERENCES tenants(id),
          rule_id TEXT NOT NULL,
          title TEXT NOT NULL,
          explanation TEXT NOT NULL,
          case_id TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(case_id,tenant_id) REFERENCES incidents(id,tenant_id)
        );
        CREATE TABLE IF NOT EXISTS synthetic_correlation_events (
          correlation_id INTEGER NOT NULL REFERENCES synthetic_correlations(id),
          event_id INTEGER NOT NULL REFERENCES synthetic_events(id),
          PRIMARY KEY(correlation_id,event_id)
        );
        CREATE INDEX IF NOT EXISTS synthetic_correlations_tenant_idx ON synthetic_correlations(tenant_id,id DESC);
        """)
        # Non-destructive migration for existing local lab DBs. Never reset
        # seeded cases or remove prior demo audit records.
        incident_fields = {row["name"] for row in db.execute("PRAGMA table_info(incidents)")}
        if "version" not in incident_fields:
            db.execute("ALTER TABLE incidents ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
        if "assigned_to" not in incident_fields:
            db.execute("ALTER TABLE incidents ADD COLUMN assigned_to TEXT")

        db.executemany("INSERT OR IGNORE INTO tenants VALUES (?,?)", TENANTS)
        db.executemany("INSERT OR IGNORE INTO identities VALUES (?,1)",
                       ((u,) for u, _, _ in ACCOUNTS))
        db.executemany("INSERT OR IGNORE INTO memberships VALUES (?,?,?,1)",
                       ((u, t, r) for u, r, t in ACCOUNTS if t))
        db.executemany("INSERT OR IGNORE INTO incidents(id,tenant_id,title,severity,status) VALUES (?,?,?,?,?)", INCIDENTS)


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=1, max_length=256)


IncidentStatus = Literal["triage", "investigating", "contained", "closed"]
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "triage": {"investigating"},
    "investigating": {"triage", "contained"},
    "contained": {"closed", "investigating"},
    "closed": {"investigating"},
}


class UpdateIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedVersion: int = Field(ge=1)
    status: IncidentStatus | None = None
    assignedTo: str | None = Field(default=None, max_length=60)


class SubmitSyntheticScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenarioId: Literal["impossible-travel", "encoded-powershell", "ordinary-signins", "partial-auth", "wazuh-ssh-burst", "wazuh-ssh-benign"]
    idempotencyKey: str = Field(min_length=12, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class AddEvidenceNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedVersion: int = Field(ge=1)
    note: str = Field(min_length=5, max_length=1000)


def incident_json(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "tenantId": row["tenant_id"],
        "title": row["title"],
        "severity": row["severity"],
        "status": row["status"],
        "version": row["version"],
        "assignedTo": row["assigned_to"],
    }


def create_app(db_path: Path, lab_password: str) -> FastAPI:
    """Create a local demo API with server-derived identities, sessions and tenant reads.

    Never expose this lab to the network or use real credentials/customer data.
    """
    if len(lab_password) < 16:
        raise ValueError("A temporary local lab password of 16+ characters is required.")
    init_database(db_path)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=list(ALLOWED_ORIGINS),
                       allow_credentials=True, allow_methods=["GET", "POST", "PATCH"],
                       allow_headers=["Content-Type", "X-CSRF-Token"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    expected_password_hash = digest(lab_password)
    failures: dict[str, tuple[int, float]] = {}

    @app.middleware("http")
    async def set_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    def audit(actor: str, tenant: str | None, operation: str, outcome: str,
              target: str | None = None):
        with connect(db_path) as db:
            db.execute(
                "INSERT INTO audit_events(actor,tenant_id,operation,outcome,target,occurred_at) "
                "VALUES (?,?,?,?,?,?)",
                (actor, tenant, operation, outcome, target, datetime.now(timezone.utc).isoformat()),
            )

    def origin_allowed(request: Request):
        origin = request.headers.get("origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            raise HTTPException(403, "Origin not permitted.")

    def current_actor(request: Request):
        sid = request.cookies.get(COOKIE, "")
        if not sid or len(sid) > 256:
            audit("anonymous", None, "authentication", "denied")
            raise HTTPException(401, "Authentication required.")
        with connect(db_path) as db:
            row = db.execute(
                "SELECT s.username,s.expires_at,i.active FROM sessions s "
                "JOIN identities i ON i.username=s.username WHERE s.token_hash=?",
                (digest(sid),),
            ).fetchone()
        if not row or row["active"] != 1 or row["expires_at"] <= int(time.time()):
            audit("anonymous", None, "authentication", "denied")
            raise HTTPException(401, "Authentication required.")
        return str(row["username"])

    def scoped(actor: str, tenant: str, operation: str) -> str:
        with connect(db_path) as db:
            membership = db.execute(
                "SELECT role FROM memberships WHERE username=? AND tenant_id=? AND active=1",
                (actor, tenant),
            ).fetchone()
        if membership is None:
            audit(actor, tenant, operation, "denied")
            raise HTTPException(404, "Not found.")
        if membership["role"] not in ("soc_analyst", "soc_lead", "customer_viewer", "customer_admin"):
            audit(actor, tenant, operation, "denied")
            raise HTTPException(403, "Forbidden.")
        return str(membership["role"])

    def analyst_scope(actor: str, tenant: str, operation: str) -> None:
        role = scoped(actor, tenant, operation)
        if role not in ("soc_analyst", "soc_lead"):
            audit(actor, tenant, operation, "denied")
            raise HTTPException(403, "Analyst role required.")


    def csrf_actor(request: Request):
        origin_allowed(request)
        actor = current_actor(request)
        csrf = request.headers.get("x-csrf-token", "")
        sid = request.cookies.get(COOKIE, "")
        with connect(db_path) as db:
            row = db.execute(
                "SELECT csrf_hash FROM sessions WHERE token_hash=? AND username=?",
                (digest(sid), actor),
            ).fetchone()
        if not row or not csrf or not hmac.compare_digest(digest(csrf), row["csrf_hash"]):
            audit(actor, None, "csrf", "denied")
            raise HTTPException(403, "CSRF check failed.")
        return actor

    @app.get("/api/health")
    def health():
        return {"service": "rh-sentry-lab", "mode": "synthetic-local-only", "liveSensors": 0}

    @app.post("/api/lab/login")
    def login(body: Login, request: Request, response: Response):
        origin_allowed(request)
        count, locked_until = failures.get(body.username, (0, 0))
        if locked_until > time.monotonic():
            raise HTTPException(429, "Temporary local login lockout.")
        with connect(db_path) as db:
            identity = db.execute("SELECT active FROM identities WHERE username=?",
                                  (body.username,)).fetchone()
        valid = (hmac.compare_digest(digest(body.password), expected_password_hash)
                 and identity is not None and identity["active"] == 1)
        if not valid:
            count += 1
            failures[body.username] = (0 if count >= 5 else count,
                                       time.monotonic() + 60 if count >= 5 else 0)
            audit(body.username, None, "login", "denied")
            raise HTTPException(401, "Invalid lab credentials.")
        failures.pop(body.username, None)
        token, csrf = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
        with connect(db_path) as db:
            db.execute("INSERT INTO sessions VALUES (?,?,?,?)",
                       (digest(token), digest(csrf), body.username, int(time.time()) + SESSION_SECONDS))
        response.set_cookie(COOKIE, token, httponly=True, secure=False,
                            samesite="strict", max_age=SESSION_SECONDS, path="/api")
        audit(body.username, None, "login", "allowed")
        return {"user": body.username, "csrfToken": csrf, "expiresInSeconds": SESSION_SECONDS}

    @app.post("/api/lab/logout")
    def logout(request: Request, response: Response, actor: str = Depends(csrf_actor)):
        with connect(db_path) as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?",
                       (digest(request.cookies.get(COOKIE, "")),))
        response.delete_cookie(COOKIE, path="/api", samesite="strict")
        audit(actor, None, "logout", "allowed")
        return {"loggedOut": True}

    @app.get("/api/me")
    def me(actor: str = Depends(current_actor)):
        with connect(db_path) as db:
            rows = db.execute(
                "SELECT tenant_id,role FROM memberships WHERE username=? AND active=1 ORDER BY tenant_id",
                (actor,),
            ).fetchall()
        audit(actor, None, "me:read", "allowed")
        return {"user": actor, "memberships": [
            {"tenantId": r["tenant_id"], "role": r["role"]} for r in rows
        ], "demoOnly": True}

    @app.get("/api/tenants")
    def tenants(actor: str = Depends(current_actor)):
        with connect(db_path) as db:
            rows = (db.execute("SELECT id,name FROM tenants ORDER BY name").fetchall()
                    if actor == "lab-auditor" else db.execute(
                        "SELECT t.id,t.name FROM tenants t JOIN memberships m ON m.tenant_id=t.id "
                        "WHERE m.username=? AND m.active=1 ORDER BY t.name", (actor,),
                    ).fetchall())
        audit(actor, None, "tenants:list", "allowed")
        return {"items": [{"id": r["id"], "name": r["name"]} for r in rows]}

    @app.get("/api/tenants/{tenant_id}/incidents")
    def incident_list(tenant_id: str, actor: str = Depends(current_actor)):
        scoped(actor, tenant_id, "incidents:list")
        with connect(db_path) as db:
            rows = db.execute(
                "SELECT id,tenant_id,title,severity,status,version,assigned_to FROM incidents "
                "WHERE tenant_id=? ORDER BY id DESC", (tenant_id,),
            ).fetchall()
        audit(actor, tenant_id, "incidents:list", "allowed")
        return {"tenantId": tenant_id, "items": [incident_json(r) for r in rows]}

    @app.get("/api/tenants/{tenant_id}/incidents/{incident_id}")
    def incident_detail(tenant_id: str, incident_id: str,
                        actor: str = Depends(current_actor)):
        scoped(actor, tenant_id, "incidents:read")
        with connect(db_path) as db:
            row = db.execute(
                "SELECT id,tenant_id,title,severity,status,version,assigned_to FROM incidents "
                "WHERE tenant_id=? AND id=?", (tenant_id, incident_id),
            ).fetchone()
        if not row:
            audit(actor, tenant_id, "incidents:read", "not_found", incident_id)
            raise HTTPException(404, "Not found.")
        audit(actor, tenant_id, "incidents:read", "allowed", incident_id)
        return incident_json(row)


    # RH Sentry local incident-management proof of concept:
    # All mutations require a server-authenticated analyst and session-bound CSRF.
    # The original SocTalk API and all live systems remain untouched.

    @app.get("/api/tenants/{tenant_id}/analysts")
    def tenant_analysts(tenant_id: str, actor: str = Depends(current_actor)):
        analyst_scope(actor, tenant_id, "analysts:list")
        with connect(db_path) as db:
            rows = db.execute(
                "SELECT m.username, m.role FROM memberships m "
                "JOIN identities i ON i.username=m.username "
                "WHERE m.tenant_id=? AND m.active=1 AND i.active=1 "
                "AND m.role IN ('soc_analyst','soc_lead') ORDER BY m.username",
                (tenant_id,),
            ).fetchall()
        audit(actor, tenant_id, "analysts:list", "allowed")
        return {"tenantId": tenant_id, "items": [
            {"username": r["username"], "role": r["role"]} for r in rows
        ]}

    @app.patch("/api/tenants/{tenant_id}/incidents/{incident_id}")
    def change_incident(
        tenant_id: str, incident_id: str, body: UpdateIncident,
        actor: str = Depends(csrf_actor),
    ):
        analyst_scope(actor, tenant_id, "incident:update")
        supplied = body.model_fields_set & {"status", "assignedTo"}
        if not supplied or ("status" in supplied and body.status is None):
            raise HTTPException(422, "Provide a new status or an assignment.")
        if "assignedTo" in supplied and body.assignedTo is not None and not body.assignedTo.strip():
            raise HTTPException(422, "Empty assignee is not valid; use null to clear.")

        with connect(db_path) as db:
            db.execute("BEGIN IMMEDIATE")  # Serialize competing local updates.
            current = db.execute(
                "SELECT id,tenant_id,title,severity,status,version,assigned_to FROM incidents "
                "WHERE tenant_id=? AND id=?", (tenant_id, incident_id),
            ).fetchone()
            if not current:
                raise HTTPException(404, "Not found.")
            if current["version"] != body.expectedVersion:
                raise HTTPException(409, "Incident changed. Refresh before saving.")
            new_status = body.status if "status" in supplied else current["status"]
            new_assignee = body.assignedTo if "assignedTo" in supplied else current["assigned_to"]
            if new_status != current["status"] and new_status not in ALLOWED_TRANSITIONS.get(current["status"], set()):
                raise HTTPException(409, "Invalid status transition for this case.")
            if new_assignee is not None:
                assignee = db.execute(
                    "SELECT 1 FROM memberships m JOIN identities i ON i.username=m.username "
                    "WHERE m.username=? AND m.tenant_id=? AND m.active=1 AND i.active=1 "
                    "AND m.role IN ('soc_analyst','soc_lead')",
                    (new_assignee, tenant_id),
                ).fetchone()
                if not assignee:
                    raise HTTPException(422, "Select an active analyst assigned to this organisation.")
            if new_status == current["status"] and new_assignee == current["assigned_to"]:
                raise HTTPException(422, "No incident changes were submitted.")
            modified = db.execute(
                "UPDATE incidents SET status=?, assigned_to=?, version=version+1 "
                "WHERE tenant_id=? AND id=? AND version=?",
                (new_status, new_assignee, tenant_id, incident_id, body.expectedVersion),
            )
            if modified.rowcount != 1:
                raise HTTPException(409, "Incident changed. Refresh before saving.")
            new_version = body.expectedVersion + 1
            at = datetime.now(timezone.utc).isoformat()
            detail = (
                f"status:{current['status']}->{new_status}; "
                f"assigned_to:{current['assigned_to'] or 'unassigned'}->{new_assignee or 'unassigned'}"
            )
            db.execute(
                "INSERT INTO incident_history(tenant_id,incident_id,actor,action,detail,version,occurred_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (tenant_id, incident_id, actor, "case_updated", detail, new_version, at),
            )
            db.execute(
                "INSERT INTO audit_events(actor,tenant_id,operation,outcome,target,occurred_at) "
                "VALUES (?,?,?,?,?,?)",
                (actor, tenant_id, "incident:update", "allowed", incident_id, at),
            )
            updated = db.execute(
                "SELECT id,tenant_id,title,severity,status,version,assigned_to FROM incidents "
                "WHERE tenant_id=? AND id=?", (tenant_id, incident_id),
            ).fetchone()
            return incident_json(updated)

    @app.post("/api/tenants/{tenant_id}/incidents/{incident_id}/evidence", status_code=201)
    def add_evidence(
        tenant_id: str, incident_id: str, body: AddEvidenceNote,
        actor: str = Depends(csrf_actor),
    ):
        analyst_scope(actor, tenant_id, "evidence:create")
        # Only plain-text synthetic analyst notes; no links, file upload,
        # markup, executable artefacts or network fetches are supported.
        note = body.note.strip()
        if len(note) < 5 or any(x in note.lower() for x in
              ("http://", "https://", "file://", "javascript:", "data:")) or "<" in note or ">" in note:
            raise HTTPException(422, "Only plain-text lab notes without URLs or markup are accepted.")
        with connect(db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT version FROM incidents WHERE tenant_id=? AND id=?",
                (tenant_id, incident_id),
            ).fetchone()
            if not current:
                raise HTTPException(404, "Not found.")
            if current["version"] != body.expectedVersion:
                raise HTTPException(409, "Incident changed. Refresh before saving.")
            now = datetime.now(timezone.utc).isoformat()
            record = db.execute(
                "INSERT INTO incident_evidence(tenant_id,incident_id,actor,kind,note,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (tenant_id, incident_id, actor, "analyst_note", note, now),
            )
            updated = db.execute(
                "UPDATE incidents SET version=version+1 WHERE tenant_id=? AND id=? AND version=?",
                (tenant_id, incident_id, body.expectedVersion),
            )
            if updated.rowcount != 1:
                raise HTTPException(409, "Incident changed. Refresh before saving.")
            version = body.expectedVersion + 1
            db.execute(
                "INSERT INTO incident_history(tenant_id,incident_id,actor,action,detail,version,occurred_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (tenant_id, incident_id, actor, "evidence_added", f"Analyst note #{record.lastrowid} added.", version, now),
            )
            db.execute(
                "INSERT INTO audit_events(actor,tenant_id,operation,outcome,target,occurred_at) "
                "VALUES (?,?,?,?,?,?)",
                (actor, tenant_id, "evidence:create", "allowed", incident_id, now),
            )
            return {"id": record.lastrowid, "incidentId": incident_id, "tenantId": tenant_id,
                    "kind": "analyst_note", "note": note, "actor": actor, "createdAt": now, "version": version}

    @app.get("/api/tenants/{tenant_id}/incidents/{incident_id}/evidence")
    def list_evidence(tenant_id: str, incident_id: str, actor: str = Depends(current_actor)):
        analyst_scope(actor, tenant_id, "evidence:list")
        with connect(db_path) as db:
            incident = db.execute(
                "SELECT 1 FROM incidents WHERE tenant_id=? AND id=?", (tenant_id, incident_id),
            ).fetchone()
            if not incident:
                raise HTTPException(404, "Not found.")
            rows = db.execute(
                "SELECT id,actor,kind,note,created_at FROM incident_evidence "
                "WHERE tenant_id=? AND incident_id=? ORDER BY id DESC LIMIT 100",
                (tenant_id, incident_id),
            ).fetchall()
        audit(actor, tenant_id, "evidence:list", "allowed", incident_id)
        return {"tenantId": tenant_id, "incidentId": incident_id, "items": [
            {"id": r["id"], "actor": r["actor"], "kind": r["kind"],
             "note": r["note"], "createdAt": r["created_at"]} for r in rows
        ]}

    @app.get("/api/tenants/{tenant_id}/incidents/{incident_id}/history")
    def incident_history(tenant_id: str, incident_id: str, actor: str = Depends(current_actor)):
        analyst_scope(actor, tenant_id, "history:list")
        with connect(db_path) as db:
            incident = db.execute(
                "SELECT 1 FROM incidents WHERE tenant_id=? AND id=?", (tenant_id, incident_id),
            ).fetchone()
            if not incident:
                raise HTTPException(404, "Not found.")
            rows = db.execute(
                "SELECT id,actor,action,detail,version,occurred_at FROM incident_history "
                "WHERE tenant_id=? AND incident_id=? ORDER BY id DESC LIMIT 100",
                (tenant_id, incident_id),
            ).fetchall()
        audit(actor, tenant_id, "history:list", "allowed", incident_id)
        return {"tenantId": tenant_id, "incidentId": incident_id, "items": [
            {"id": r["id"], "actor": r["actor"], "action": r["action"],
             "detail": r["detail"], "version": r["version"],
             "occurredAt": r["occurred_at"]} for r in rows
        ]}

    # Isolated, synthetic-only event pipeline. All ingested event content is
    # generated server-side from a fixed catalogue; user-provided telemetry,
    # external URLs, arbitrary commands and file uploads are not accepted.

    @app.get("/api/tenants/{tenant_id}/lab/scenarios")
    def list_synthetic_scenarios(tenant_id: str, actor: str = Depends(current_actor)):
        analyst_scope(actor, tenant_id, "synthetic:scenarios")
        return {"tenantId": tenant_id, "items": scenario_catalogue(), "liveIngestion": False}

    @app.post("/api/tenants/{tenant_id}/lab/scenarios/ingest", status_code=201)
    def ingest_synthetic_scenario(
        tenant_id: str, body: SubmitSyntheticScenario, response: Response,
        actor: str = Depends(csrf_actor),
    ):
        analyst_scope(actor, tenant_id, "synthetic:ingest")
        # An idempotency token is scoped to an authenticated tenant.
        # It cannot be used to smuggle arbitrary logs or choose an incident.
        with connect(db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT id,scenario_id FROM synthetic_event_batches "
                "WHERE tenant_id=? AND idempotency_key=?",
                (tenant_id, body.idempotencyKey),
            ).fetchone()
            if existing is not None:
                if existing["scenario_id"] != body.scenarioId:
                    raise HTTPException(409, "Idempotency token belongs to another scenario.")
                response.status_code = 200
                return {
                    "tenantId": tenant_id, "batchId": existing["id"],
                    "scenarioId": existing["scenario_id"], "replayed": True,
                }
            # Bound disk growth in this temporary localhost lab.
            count = db.execute(
                "SELECT COUNT(*) AS n FROM synthetic_event_batches WHERE tenant_id=?",
                (tenant_id,),
            ).fetchone()["n"]
            if count >= 50:
                raise HTTPException(429, "Local synthetic batch limit reached for this tenant.")
            events, matches = generate_scenario(body.scenarioId, tenant_id)
            now = datetime.now(timezone.utc).isoformat()
            batch_id = db.execute(
                "INSERT INTO synthetic_event_batches "
                "(tenant_id,idempotency_key,scenario_id,submitted_by,created_at) "
                "VALUES (?,?,?,?,?)",
                (tenant_id, body.idempotencyKey, body.scenarioId, actor, now),
            ).lastrowid
            event_ids = []
            for event in events:
                event_ids.append(db.execute(
                    "INSERT INTO synthetic_events "
                    "(batch_id,tenant_id,event_type,occurred_at,source,actor,host,description,attributes_json) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (batch_id, tenant_id, event["event_type"], event["occurred_at"],
                     event["source"], event["actor"], event["host"], event["description"],
                     json.dumps(event["attributes"], sort_keys=True)),
                ).lastrowid)
            for match in matches:
                correlation_id = db.execute(
                    "INSERT INTO synthetic_correlations "
                    "(batch_id,tenant_id,rule_id,title,explanation,case_id,created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (batch_id, tenant_id, match["rule_id"], match["title"],
                     match["explanation"], match["case_id"], now),
                ).lastrowid
                db.executemany(
                    "INSERT INTO synthetic_correlation_events(correlation_id,event_id) VALUES (?,?)",
                    ((correlation_id, event_ids[index]) for index in match["event_offsets"]),
                )
            db.execute(
                "INSERT INTO audit_events(actor,tenant_id,operation,outcome,target,occurred_at) "
                "VALUES (?,?,?,?,?,?)",
                (actor, tenant_id, "synthetic:ingest", "allowed", f"batch:{batch_id}", now),
            )
            return {
                "tenantId": tenant_id, "batchId": batch_id,
                "scenarioId": body.scenarioId, "replayed": False,
                "eventCount": len(event_ids), "correlationCount": len(matches),
            }

    @app.get("/api/tenants/{tenant_id}/lab/events")
    def synthetic_event_list(tenant_id: str, actor: str = Depends(current_actor)):
        analyst_scope(actor, tenant_id, "synthetic:events:list")
        with connect(db_path) as db:
            rows = db.execute(
                "SELECT id,batch_id,event_type,occurred_at,source,actor,host,description,attributes_json "
                "FROM synthetic_events WHERE tenant_id=? ORDER BY id DESC LIMIT 100",
                (tenant_id,),
            ).fetchall()
        audit(actor, tenant_id, "synthetic:events:list", "allowed")
        return {"tenantId": tenant_id, "items": [{
            "id": row["id"], "batchId": row["batch_id"], "eventType": row["event_type"],
            "occurredAt": row["occurred_at"], "source": row["source"],
            "actor": row["actor"], "host": row["host"],
            "description": row["description"], "attributes": json.loads(row["attributes_json"]),
        } for row in rows], "liveTelemetry": False}

    @app.get("/api/tenants/{tenant_id}/lab/correlations")
    def synthetic_correlation_list(tenant_id: str, actor: str = Depends(current_actor)):
        analyst_scope(actor, tenant_id, "synthetic:correlations:list")
        with connect(db_path) as db:
            rows = db.execute(
                "SELECT id,batch_id,rule_id,title,explanation,case_id,created_at "
                "FROM synthetic_correlations WHERE tenant_id=? ORDER BY id DESC LIMIT 100",
                (tenant_id,),
            ).fetchall()
            items = []
            for row in rows:
                # Explicit tenant check via joined event record prevents a
                # foreign event reference being surfaced in the wrong tenant.
                links = db.execute(
                    "SELECT e.id FROM synthetic_correlation_events ce "
                    "JOIN synthetic_events e ON e.id=ce.event_id "
                    "WHERE ce.correlation_id=? AND e.tenant_id=? ORDER BY e.id",
                    (row["id"], tenant_id),
                ).fetchall()
                items.append({
                    "id": row["id"], "batchId": row["batch_id"],
                    "ruleId": row["rule_id"], "title": row["title"],
                    "explanation": row["explanation"], "caseId": row["case_id"],
                    "eventIds": [link["id"] for link in links],
                    "createdAt": row["created_at"],
                })
        audit(actor, tenant_id, "synthetic:correlations:list", "allowed")
        return {"tenantId": tenant_id, "items": items, "liveDetection": False}

    @app.get("/api/lab/audit")
    def audit_history(actor: str = Depends(current_actor)):
        if actor != "lab-auditor":
            audit(actor, None, "audit:read", "denied")
            raise HTTPException(403, "Forbidden.")
        with connect(db_path) as db:
            rows = db.execute(
                "SELECT id,actor,tenant_id,operation,outcome,target,occurred_at "
                "FROM audit_events ORDER BY id DESC LIMIT 100"
            ).fetchall()
        return {"items": [dict(row) for row in rows], "demoOnly": True}

    return app
