# RH Sentry localhost API lab

**Development-only, fictional-data reference service.** It is not an operational SOC, production identity system, deployable SaaS backend or security assurance. It does not alter the original SocTalk backend. Never put real customer records, credentials, logs, emails or confidential company data into this lab.

This folder exists to test the first real HTTP and SQLite boundaries before designing the proprietary RH Sentry backend in a **private** repository.

## Included

- Python FastAPI service, **exclusively started by** run.py, listening on 127.0.0.1:8001
- Manually supplied temporary lab password, no default credentials
- Server-issued opaque HttpOnly session cookie; only its hash is stored in SQLite
- One-hour sessions, logout with session-bound CSRF token and explicit origin checks
- Fixed CORS origins restricted to local SvelteKit development server
- Fictional identities and memberships resolved server-side
- SQL queries scoped to owning tenant, with 404 for unauthorised cross-tenant requests
- Persistent *fictional* incident records and lab audit entries, stored in local SQLite
- Read-only customer incident access plus **analyst-only** status changes, assignment and plain-text evidence notes, with CSRF and concurrency checks
- No endpoint isolation, account revocation, script execution or other real SOC response actions
- Python tests covering session, tenancy, CSRF, audit and persistence

**Important limitations:** The fictional accounts share a single developer-supplied password. Cookie Secure is false because the server uses loopback HTTP. Access controls and audit are educational examples, not security-reviewed production systems; no OIDC/MFA, HTTPS, lifecycle management, real RBAC administration, tamper-evident audit, rate limiting across processes, or verified SIEM is provided.

## Start from VS Code on Windows

Keep the frontend development server running at \`http://127.0.0.1:5173\`. Use a **second** VS Code PowerShell terminal from your repo root (\`soctalk\`):

\`\`\`powershell
cd dev\rh_sentry_lab_api
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q tests

$secret = Read-Host "Create a temporary local test password (16+ characters)" -AsSecureString
$env:RH_SENTRY_LAB_PASSWORD = [System.Net.NetworkCredential]::new("", $secret).Password
.\.venv\Scripts\python.exe run.py
\`\`\`

Use a unique lab password you can retype in the preview. **Never reuse a business login.** If \`py -3\` isn't found, install a supported Python 3.11–3.13 interpreter for Windows first. The app uses Python 3.11+ typing features.

**Already running the API?** After pulling, stop the backend using Ctrl+C and restart it from the same PowerShell terminal using the existing `run.py` command. The environment password remains available in that PowerShell session. The database schema migrates non-destructively, preserving existing synthetic records.

The local lab reads/writes only \`%USERPROFILE%\.rh-sentry-lab\sentry-lab.sqlite3\` by default; you can override this with \`RH_SENTRY_LAB_DB\` for disposable tests. The database location is outside the Git repository and stays on your device. To stop the API press Ctrl+C in its terminal.

After starting the API, open the frontend at:

\`http://127.0.0.1:5173/sentry-preview\`

Choose **API Lab**. It should show **LOCAL API ONLINE**. Choose one of the fictional accounts, type the temporary lab password and sign in. Your browser receives a local-only cookie. Keep the frontend and API on **127.0.0.1**, not a mix of localhost and 127.0.0.1, because Strict cookies are intentionally used.

### Suggested acceptance checks

1. Log in as **alderwick-viewer**. You should see only Alderwick's two incidents.
2. In the cross-tenant test, request **summit**. The local API should respond **404**, not return Summit's records.
3. Log out. Incident reads should require login again.
4. Log in as **summit-viewer**. You should now see only Summit's two incidents.
5. Log in as **lab-auditor**. You can see fictional organisation metadata and request the lab audit journal, but may **not** read any tenant's incident records.
6. Stop and restart the API. Records and audit history should still be in SQLite.
7. Confirm the existing SocTalk frontend and backend are otherwise unchanged.

## API endpoints

| Method | Path | Behaviour |
|---|---|---|
| GET | /api/health | Local lab status, no live sensors |
| POST | /api/lab/login | Fictional username + temporary local lab password; returns CSRF token and session cookie |
| POST | /api/lab/logout | Requires matching session cookie and CSRF token |
| GET | /api/me | Server-derived identity and memberships |
| GET | /api/tenants | Only member tenants; fictional auditor sees metadata |
| GET | /api/tenants/{tenantId}/incidents | Checks active membership and scopes SQL WHERE tenant_id=? |
| GET | /api/tenants/{tenantId}/incidents/{id} | Checks membership and resource ownership in query |
| GET | /api/lab/audit | Lab auditor only; returns latest 100 local records |

The browser cannot submit arbitrary identities or grant itself permissions. The local password and fictional usernames are not production authentication.

## What comes next (not implemented)

Move to a private Red Horizon repository; replace the shared lab password with production-grade OIDC sessions, MFA and role lifecycle; migrate to a properly governed data store; enforce tenant ownership in all queries and workers; introduce durable audit and session revocation; perform independent isolation and security testing; only then integrate SIEM telemetry or AI.

No Wazuh, real AI, managed security monitoring or response execution is connected by this project.

## Persistent incident-management milestone

The browser now supports an analyst-only case editor with status changes, assignment, evidence notes and versioned history stored in local SQLite:

- `PATCH /api/tenants/{tenantId}/incidents/{incidentId}` — analyst-only status and assignment; requires CSRF and current `expectedVersion`.
- `GET /api/tenants/{tenantId}/analysts` — analysts in the same synthetic tenant.
- `POST /api/tenants/{tenantId}/incidents/{incidentId}/evidence` — analyst-only plain-text note (5–1000 characters), with expected version. No uploads, URLs or markup.
- `GET /api/tenants/{tenantId}/incidents/{incidentId}/evidence` — analyst-only note history.
- `GET /api/tenants/{tenantId}/incidents/{incidentId}/history` — analyst-only versioned case changes.

Each successful change atomically updates the incident version, records the case event and adds a local audit entry. Outdated versions receive **409**; cross-tenant requests return **404**; customer viewers cannot modify cases (**403**). These safeguards are tested only in the isolated lab.

### Try the new screen

1. Sign out of `alderwick-viewer` in **API Lab**.
2. Sign in as `alderwick-analyst` using the same temporary lab password.
3. Select `SEN-2047`, change its status from **triage** to **investigating**, and optionally assign `alderwick-lead`.
4. Add a fictional investigation note; check the Evidence Register and Change History.
5. Restart the API and confirm the case changes persist.
6. Sign in as `alderwick-viewer`; the case stays visible but editing and internal analyst notes are unavailable.

**Never use genuine client records or secrets here.** The local SQLite file is not encrypted or governed for real customer information.


## Synthetic event ingestion and correlation laboratory

A separate, **fictional-data-only** event pipeline is available in the RH Sentry preview at **Event Pipeline**. The Python service must be restarted after pulling new backend code so its SQLite migrations run.

Only an authenticated fictional SOC analyst/lead in the owning tenant may list or ingest these scenarios. Ingestion requires the same session-bound CSRF token as incident edits. There is no real SIEM, Wazuh integration, event collector, AI model, external file/URL import or automated response.

| Method | Lab path | Purpose |
| --- | --- | --- |
| GET | /api/tenants/{tenantId}/lab/scenarios | List four fixed synthetic scenario definitions |
| POST | /api/tenants/{tenantId}/lab/scenarios/ingest | Generate one fixed event batch, using a validated scenarioId and idempotencyKey |
| GET | /api/tenants/{tenantId}/lab/events | Read the most recent 100 fictional events for authorised tenant |
| GET | /api/tenants/{tenantId}/lab/correlations | Read 100 synthetic correlations, linked source event IDs and optional existing case references |

The generator provides *impossible travel*, *encoded PowerShell*, *ordinary sign-ins* and *incomplete authentication telemetry* examples. Only the first two produce positive illustrative matches; benign and incomplete examples must not. Synthetic events include source, event time, type, fictional actor/host and small controlled attributes; no raw user-supplied events can be imported.

Security/control properties in this local lab: server-validated tenancy, analyst-role restriction, CSRF for writes, tenant-scoped SQL, atomic transaction per batch, tenant-keyed idempotency (retry does not duplicate events), a 50-batch-per-tenant disk-growth limit, and audit entries. Correlation references an existing synthetic case only when one belongs to the same tenant; it never creates a new case or updates its status. Test cases verify these conditions. This does not constitute production-grade isolation, real detection fidelity or monitoring coverage.

### Test on your laptop

1. Pull branch \`dev/rh-one\` from the root \`soctalk\` directory, preserving any local work first.
2. In your Python backend terminal at \`dev\rh_sentry_lab_api\`, stop the server with Ctrl+C, then restart \`.\.venv\Scripts\python.exe run.py\`. Keep your already-created temporary lab password in that PowerShell session.
3. In another terminal, keep the Svelte frontend on \`127.0.0.1:5173\`.
4. Under **API Lab**, sign in again as \`alderwick-analyst\` to obtain an in-memory CSRF token.
5. Open **Event Pipeline**, select *Unusual consecutive sign-ins* and click **Generate & correlate sample batch**.
6. Expect **two stored synthetic events** and one correlation labelled \`RHS-DET-001\`; click the link to existing incident \`SEN-2048\` in local Incidents mode. The case status should not have changed.
7. Return and test the *ordinary sign-ins* and *incomplete sign-in* scenarios: no new correlations should appear for their batches. Historical correlations from other batches remain visible.
8. Sign in as \`alderwick-viewer\` to confirm analyst event access is denied. A full browser refresh may require signing in again before submitting events.
9. Run \`.\.venv\Scripts\python.exe -m pytest -q tests\` in the Python lab folder to verify the security and persistence checks.

The intentionally bounded test generator must never be exposed to external networks or real organisations. When the lab reaches 50 synthetic batches for a tenant it refuses additional ingestion rather than silently deleting audit/event records.
