"""Local-only RH Sentry API laboratory. Fictional data; not production auth.

Run exclusively through run.py, which binds to the loopback interface.
Existing SocTalk backend and production deployments are untouched.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

COOKIE = "rh_sentry_lab_session"
SESSION_SECONDS = 3600
ALLOWED_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")
TENANTS = [("alderwick", "Alderwick Logistics"), ("harbourline", "Harbourline Legal"),
           ("summit", "Summit Retail")]
# One temporary user password for all fictional lab identities, supplied at
# runtime via environment variable. Not acceptable for a commercial product.
ACCOUNTS = [
    ("alderwick-analyst", "soc_analyst", "alderwick"),
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
        """)
        db.executemany("INSERT OR IGNORE INTO tenants VALUES (?,?)", TENANTS)
        db.executemany("INSERT OR IGNORE INTO identities VALUES (?,1)",
                       ((u,) for u, _, _ in ACCOUNTS))
        db.executemany("INSERT OR IGNORE INTO memberships VALUES (?,?,?,1)",
                       ((u, t, r) for u, r, t in ACCOUNTS if t))
        db.executemany("INSERT OR IGNORE INTO incidents VALUES (?,?,?,?,?)", INCIDENTS)


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=1, max_length=256)


def create_app(db_path: Path, lab_password: str) -> FastAPI:
    """Create a local demo API with server-derived identities, sessions and tenant reads.

    Never expose this lab to the network or use real credentials/customer data.
    """
    if len(lab_password) < 16:
        raise ValueError("A temporary local lab password of 16+ characters is required.")
    init_database(db_path)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=list(ALLOWED_ORIGINS),
                       allow_credentials=True, allow_methods=["GET", "POST"],
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

    def scoped(actor: str, tenant: str, operation: str):
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
                "SELECT id,tenant_id,title,severity,status FROM incidents "
                "WHERE tenant_id=? ORDER BY id DESC", (tenant_id,),
            ).fetchall()
        audit(actor, tenant_id, "incidents:list", "allowed")
        return {"tenantId": tenant_id, "items": [
            {"id": r["id"], "tenantId": r["tenant_id"], "title": r["title"],
             "severity": r["severity"], "status": r["status"]} for r in rows
        ]}

    @app.get("/api/tenants/{tenant_id}/incidents/{incident_id}")
    def incident_detail(tenant_id: str, incident_id: str,
                        actor: str = Depends(current_actor)):
        scoped(actor, tenant_id, "incidents:read")
        with connect(db_path) as db:
            row = db.execute(
                "SELECT id,tenant_id,title,severity,status FROM incidents "
                "WHERE tenant_id=? AND id=?", (tenant_id, incident_id),
            ).fetchone()
        if not row:
            audit(actor, tenant_id, "incidents:read", "not_found", incident_id)
            raise HTTPException(404, "Not found.")
        audit(actor, tenant_id, "incidents:read", "allowed", incident_id)
        return dict(row) | {"tenantId": row["tenant_id"]}

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
