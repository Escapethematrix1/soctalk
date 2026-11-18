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


## Wazuh JSON-format adapter (offline fixtures only)

Two additional Event Pipeline choices are now available after restarting the Python backend:

- **Wazuh-format SSH failure burst** — three manufactured Wazuh alert-shaped objects are reduced to a strict allowlist; a deterministic example correlates events sharing agent, rule and TEST-NET source IP within five minutes.
- **Wazuh-format single SSH failure** — one fabricated alert is retained without a positive burst correlation.

Wazuh's documented alert JSON convention includes top-level \`timestamp\` and \`id\`, nested \`rule.id/level/description\`, \`agent.id/name\`, and optional \`data\`. The lab's deliberately limited adapter in [wazuh_fixture_adapter.py](wazuh_fixture_adapter.py) retains only those vetted fields plus \`data.srcip\`; it does **not** save raw \`full_log\`, \`previous_output\`, \`location\`, arbitrary \`data\`, or manager internals. Agent names must begin with \`TRAINING-\` and addresses must belong to RFC 5737 TEST-NET-1 (\`192.0.2.0/24\`), so the example cannot accidentally contain a real customer's source IP. The illustrative rule \`100900\` is **not** a claim about an official Wazuh ruleset ID. Existing tenant membership, CSRF, idempotency, audit and rate limits still apply.

References:

- Wazuh alert storage: https://documentation.wazuh.com/current/user-manual/manager/alert-management.html
- Wazuh JSON alert example: https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html

**This adapter has no connection to a Wazuh manager, dashboard, indexer, or agent.** It cannot ingest real alert files and cannot be used for customer monitoring. Real telemetry integration must introduce a separate authenticated, source-attested collector and establish strict per-customer provenance, rate limiting, parsing, transport encryption, deduplication, retention and review controls.

### Laptop resource planning

Official Wazuh quickstart guidance for the all-in-one Wazuh server + indexer + dashboard serving 1–25 agents is **4 vCPUs, 8 GiB RAM and 50 GB storage**: https://documentation.wazuh.com/current/quickstart.html

On a **16 GB RAM laptop**, giving 8 GB to a Wazuh VM leaves only 8 GB for Windows, VS Code, the browser and other tasks. Avoid running the existing Kali VM and a full Wazuh VM together; this is likely to cause memory pressure. Finish the offline adapter and lab tests first, then consider an isolated Wazuh-only VM session with Kali shut down, or use a different lab machine later. This branch has not provisioned any VM or installed any Wazuh package.

### Validation

From \`dev\rh_sentry_lab_api\` run \`.\.venv\Scripts\python.exe -m pytest -q tests\`, then restart the local Python server after pulling new code. In Event Pipeline, sign in through API Lab as fictional \`alderwick-analyst\` and test both Wazuh-format scenarios. A burst creates **three fictional event rows and one synthetic correlation**. A single event creates one row with **zero new correlations**. Other historical correlations remain visible. The associated test file is [tests/test_wazuh_fixture_adapter.py](tests/test_wazuh_fixture_adapter.py).


## Offline Wazuh JSONL replay validator (pre-VM readiness)

The training-only \`wazuh_replay.py\` script checks a *local fictional* Wazuh JSON-lines file before any VM or connector is enabled. It never calls a network endpoint, changes SQLite, installs Wazuh, imports real logs or touches the original SocTalk backend.

From this \`dev\rh_sentry_lab_api\` folder:

\`\`\`powershell
.\.venv\Scripts\python.exe wazuh_replay.py --file fixtures/wazuh_training_ssh.jsonl
.\.venv\Scripts\python.exe -m pytest -q tests
\`\`\`

Expected report: 3 validated fictional records, 1 example SSH-burst correlation, \`liveMonitoring: false\`, \`connectedWazuhManager: false\`, \`databaseModified: false\`. Full log and other untrusted original Wazuh fields never appear in the report.

**This is not a real Wazuh connector.** Only generated test data is accepted, using \`TRAINING-\` hostnames and TEST-NET-1 addresses \`192.0.2.0/24\`; malformed, oversized, duplicate or genuine-source-looking inputs are rejected. Keep actual \`alerts.json\` and sensitive events out of this public repository.

Follow the staged **[isolated Wazuh VirtualBox lab plan](../../RH_SENTRY_WAZUH_LAB_PLAN.md)** before attempting any real agent/manager setup. On a 16 GB Windows host, Wazuh's suggested all-in-one 8 GiB/4-vCPU/50-GB baseline requires keeping Kali powered off and evaluating host memory pressure. No VirtualBox configuration was performed by these commits.

## Persistent fictional Asset Management

Assets → Local API / SQLite now uses a versioned, customer-scoped inventory stored in the same local SQLite database. Asset registration never enrolls an endpoint or creates a monitor. All returned assets have monitoringState=not_connected and lastSeen=null.

Routes (all under /api/tenants/{tenantId}):

- GET /assets and GET /assets/{assetId} — authorised customer members can read their fictional inventory.
- POST /assets — SOC analysts/leads can register fictional assets (CSRF-protected; maximum 200 records per tenant).
- PATCH /assets/{assetId} — analysts can update approved fields using expectedVersion concurrency checks.
- GET /assets/{assetId}/incidents — tenant-scoped links to existing fictional cases.
- POST /assets/{assetId}/incidents and DELETE /assets/{assetId}/incidents/{incidentId} — analyst-only CSRF-protected, versioned links/unlinks, checked against the **same tenant**.
- GET /assets/{assetId}/history — analyst-only versioned change journal.

All successful changes commit local audit entries atomically. No monitoring state, agent identity, network target or telemetry URL can be set by the client. Initial example links are seeded only once, so a deliberate unlink persists across restarts.

### Local browser acceptance

1. Pull dev/rh-one from the soctalk repository root, preserving local modifications before pulling.
2. In the Python terminal under dev\rh_sentry_lab_api, press Ctrl+C and rerun .\.venv\Scripts\python.exe run.py. The existing lab password must be available in this PowerShell session.
3. Keep the Svelte frontend running at 127.0.0.1:5173, and sign in as fictional alderwick-analyst through API Lab.
4. Open Assets → Local API / SQLite. Expect four Alderwick training records and **00 live monitored**.
5. Select WIN-DEMO-07 and open its linked fictional incident SEN-2047. Return, register TRAINING-WIN-42, edit its lifecycle and link another case.
6. Refresh/restart and verify the new asset, version, incident associations and history persist.
7. Log in as alderwick-viewer to verify editing is unavailable; switch to Simulation to verify the earlier visual cards.
8. In Command Centre → Local API / SQLite, verify the registered-asset count changes while live monitored sensors remain zero.

Run Python API tests from the lab directory: .\.venv\Scripts\python.exe -m pytest -q tests. Automated security/unit validation does not replace local browser acceptance or commercial security review.

## Persistent synthetic Detection Engineering

RH Sentry's **Detection Engineering → Local API / SQLite** screen manages only fictional rule definitions and manual evaluations of pre-existing synthetic event batches. Rules never subscribe to Wazuh, poll devices, produce operational alert notifications, execute endpoint responses or create incidents.

Three allowlisted, fixed detection strategies are supported:

- identity_travel: two fictional sign-ins for one account within 15 minutes, from different regions, with a bounded distance threshold (100–5000 km).
- encoded_powershell: a fictional endpoint-process event flagged encoded_command=true and parent_trusted=false (fixed threshold 1).
- wazuh_ssh_burst: three or more fabricated Wazuh-format SSH failures within five minutes for the same agent, rule and reserved TEST-NET source (bounded threshold 3–20).

All authenticated endpoints below are under /api/tenants/{tenantId}/lab and **SOC analyst/lead only**. All mutations require the session's CSRF token and a permitted local browser origin.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /detection-templates | Safe strategies and threshold bounds |
| GET / POST | /detection-rules | List or register tenant-owned training rules |
| PATCH | /detection-rules/{ruleId} | Versioned changes to title, description, threshold or status |
| GET | /detection-rules/{ruleId}/history | Versioned rule modification journal |
| GET | /event-batches | Tenant-owned batches available for manual evaluation |
| POST | /detection-rules/{ruleId}/test | Idempotent test against a stored batch, saving provenance |
| GET | /detection-runs | Test version/threshold snapshots and matched event IDs |
| GET | /detection-findings | Positive synthetic matches awaiting analyst disposition |
| POST | /detection-findings/{findingId}/review | False-positive or needs-investigation review and reason |
| GET | /detection-findings/{findingId}/reviews | Read versioned disposition history |

Rules start as drafts. Test-enabled rules and drafts can be evaluated manually; disabled rules cannot. **Test-enabled is not a live detector.** A match saves a human-review training finding with supporting source IDs. A false-positive disposition is a judgement about the test fixture, not a production detection quality measurement.

Controls: fixed rule strategies, strict request schemas, bounded thresholds and test batch sizes, at most 30 local rules and 100 stored test runs per tenant, atomic SQLite transactions, optimistic concurrency, replay tokens, tenant-scoped SQL and foreign keys, auditor journal. **This does not replace production IAM, detection tuning QA, an isolated reliable ingest service or an operational SOC.**

### Local acceptance

1. From the repository root, pull dev/rh-one after preserving uncommitted work.
2. In the Python backend terminal under dev\rh_sentry_lab_api, Ctrl+C then .\.venv\Scripts\python.exe run.py. Reuse the temporary lab password configured in that terminal.
3. Keep Svelte on 127.0.0.1:5173; open /sentry-preview. Log in through API Lab as fictional alderwick-analyst.
4. In Event Pipeline create an impossible-travel synthetic batch. Return to Detection Engineering → Local API / SQLite and choose RHS-DET-001 plus that batch.
5. Run a manual test. Expect a matched result and two synthetic event IDs. A new unreviewed training finding should appear; no incident gets created.
6. Enter a 12+ character reason and review the finding as false positive. Refresh the page: stored run, outcome and review history should persist.
7. Try ordinary-signins: should return not_matched and create no finding. A disabled rule should refuse testing. Sign in as alderwick-viewer to confirm internal rule visibility is denied.
8. Switch back to Simulation and verify the original demonstration is unchanged. On Assets, + Register Asset appears in the upper toolbar for analysts with the form directly below the customer selector.

Backend checks: .\.venv\Scripts\python.exe -m pytest -q tests. Frontend checks: from frontend run pnpm check and pnpm exec vitest run src/lib/sentry-contracts src/lib/sentry-demo src/lib/sentry-lab.


## Response Centre: fictional proposals, independent approvals and dry-run receipts

**Execution remains impossible by design in this local API.** This adds structured, durable workflow records, not real defensive action or SOC staffing.

All paths below have the prefix \`/api/tenants/{tenantId}/lab\` and must pass server-side tenant membership checks:

| Method | Path | Role / effect |
| --- | --- | --- |
| GET | /response-playbooks | SOC analyst/lead; four allowlisted, non-executable playbooks |
| GET | /response-requests | SOC analyst/lead; ordered pending and completed proposals for one tenant |
| POST | /response-requests | SOC analyst/lead + CSRF; store a proposal against an existing tenant-owned incident with an idempotency key |
| POST | /response-requests/{id}/decision | **Independent SOC lead** + CSRF + version; approve *dry-run only* or reject, with a reason |
| POST | /response-requests/{id}/simulate | SOC lead + CSRF + version; store a simulated receipt only if previously approved |
| GET | /response-requests/{id}/history | SOC analyst/lead; read append-only decision and receipt history |

No proposal may refer to another tenant's incident. A lead cannot approve their own proposal. Requests do not change incidents or detection findings. SQL tenant-bound foreign keys, record version checks, audit records and a 100-proposal-per-tenant training limit apply. API outputs always report \`liveExecution: false\`; dry-run receipts always report \`externalActions: 0\`.

### Local acceptance

1. Pull the \`dev/rh-one\` development branch in the soctalk root, preserving any local edits.
2. Restart **Python backend** (Ctrl+C then \`.\.venv\Scripts\python.exe run.py\` under \`dev\rh_sentry_lab_api\`) so SQLite creates the new tables without resetting cases or assets. Reuse your existing temporary lab password in that terminal.
3. Keep **frontend** on \`127.0.0.1:5173\`, and open \`http://127.0.0.1:5173/sentry-preview\`.
4. Sign in through **API Lab** as fictional \`alderwick-analyst\`. RH Sentry defaults to local persisted mode. Open **Response Centre → Local API / SQLite**.
5. Use **+ Propose response**. Select case \`SEN-2048\` and the **Verify unusual sign-in** template. Give a 15+ character reason and save. The new proposal should be pending.
6. Log out of API Lab, sign in as fictional \`alderwick-lead\`, return to Response Centre and select the proposal. Document an independent approval/rejection reason.
7. After approving a **dry-run**, use **Record dry-run receipt**. Verify the receipt shows zero external actions, no case changes, and an audit history. Refresh or restart the backend: the saved decision should remain.
8. Sign in as \`alderwick-viewer\` to confirm internal Response Centre records are restricted. Switch to **Simulation** to verify the earlier visual demonstration remains available.
9. Use global **Find a feature** and search for \`approve response\` or \`register asset\`. Verify it shows the corresponding real steps and opens the intended page. On initial launch, the sidebar displays only five core sections; toggle **Advanced tools** for engineering and lab screens.

Automated validation: \`.\.venv\Scripts\python.exe -m pytest -q tests\`. The frontend CI exercises Svelte typechecking and navigation registry/unit tests. This is **not production-ready**; VMs and Wazuh are deferred until the full software and security infrastructure is built.

### Future AI Analyst navigation tool

The versioned frontend registry lives at \`frontend/src/lib/sentry-contracts/platform-guide.ts\`. Future AI-enabled navigation must use that reviewed source or a server-issued equivalent, resolve the currently authorised tenant and role, and answer with an actual available destination. The current guide is searchable **deterministic UI help**, not an LLM, and should not be represented to customers as live AI.
