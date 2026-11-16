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
- No executable response endpoints; only GET, login and logout
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
