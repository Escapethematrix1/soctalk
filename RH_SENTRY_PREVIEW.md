# RH Sentry — interactive design preview

**Product:** RH Sentry, Red Horizon Cyber Group's planned AI-native SOC SaaS.  
**Working branch:** `dev/rh-one` (legacy branch name; RH Sentry is a separate product from Red Horizon One).  
**Preview:** `http://127.0.0.1:5173/sentry-preview`  
**Status:** local development only. **No live security protection.**

## See the preview on Windows (PowerShell)

From your existing `RH_SOC/soctalk` folder in VS Code:

```powershell
git status --short
git pull --ff-only origin dev/rh-one
cd frontend
pnpm check
pnpm dev --host 127.0.0.1
```

If you are already in the `frontend` directory, **do not run `cd frontend` again**. If another Vite dev server is running, stop it with Ctrl+C before restarting. Keep the terminal open.

Open `http://127.0.0.1:5173/sentry-preview`. This new route intentionally bypasses the existing SocTalk sidebar, login check and backend API calls. The original pages remain untouched. If a link opens the older `/login` page instead, ensure the address ends with `/sentry-preview` and your local branch contains the latest commit.

## What to try

- Switch between Command Centre, Incidents, AI Analyst, Assets and Reports using the custom sidebar.
- Filter cases by severity and search by name/asset.
- Select a sample incident to inspect its evidence and narrative.
- Click **Inject demo alert** to add a synthetic case locally in your browser.
- Generate a sample executive briefing and click **Reset demo** to restore original sample data.

All incidents, security metrics, assets and AI confidence percentages are **fictional**; they are not fetched from a SIEM or AI service. No actual enforcement, endpoint isolation, or account changes occur. The label **DEMO ENVIRONMENT** is deliberately persistent.

## Brand and architecture safeguards

- Working brand name **RH Sentry**. No invented Red Horizon monogram/logo has been created; insert only an approved supplied logo later.
- The preview is a new isolated SvelteKit route. Existing API clients and current SocTalk dashboard remain untouched.
- A dev-only page load guard prevents navigation to this prototype in production builds. Production auth, tenancy and incident response will require separate implementation and independent testing.
- Do not connect production customer accounts or real confidential logs to this prototype.
- Some existing SocTalk routes may still show backend connection failures until its backend is configured; those failures do not affect this isolated preview.


## Stage 2 — AI Analyst workbench (added)

The **AI Analyst** section now provides:

- A searchable investigation queue with selectable sample cases.
- A preauthored investigative question, working hypothesis, benign alternative and explicit evidence gaps.
- A sample evidence register, verification steps and illustrative ATT&CK context.
- A human review screen with approve/reject decisions that update **only local Svelte component state**. They do not transmit anything, execute endpoint changes or grant real privileges.
- Case-specific run/decision state that remains while switching between RH Sentry preview sections; **Reset demo** clears it.

**These are deterministic examples, not an operational AI analyst.** No model, Wazuh ingestion, backend, real customers, alerts, agent enrollment, audit persistence or response service is connected.

### Refresh the project after this commit

If your VS Code terminal currently ends in \`...\soctalk\frontend\`, run:

\`\`\`powershell
cd ..
git pull --ff-only origin dev/rh-one
cd frontend
pnpm check
pnpm test:unit
\`\`\`

The test suite includes new RH Sentry investigation-contract tests. If \`pnpm check\` reports errors, do not proceed to integration; capture the full output for debugging.

Keep or start one Vite server with \`pnpm dev --host 127.0.0.1\`, then open \`http://127.0.0.1:5173/sentry-preview\`.



## Stage 3 — Multi-customer SaaS design (added)

The new **Customers** sidebar section shows a fictional MSSP customer portfolio:

- Searchable sample organisations and tenant-specific incident summaries.
- A toggle between an operator-facing workspace and a **visual customer-portal preview**.
- Customer-scoped *sample* incident lists and separate demonstration counts.
- Clear warning that this toggle is **not** authentication, isolation or an actual tenant boundary.
- Zero live sensors, no real customers, and no connected databases.

The AI Analyst typography and column proportions have also been adjusted for readability.

All customer names and \`.invalid\` email addresses are fabricated. A real SaaS release needs enforced server-side tenant authorisation, tested data partitioning, identity management and comprehensive audit logging. A client-side filter alone is **never** an acceptable security boundary.

The team should verify this milestone using \`pnpm check\`, \`pnpm test:unit\` and the localhost preview. This GitHub edit has **not** been executed on the developer's laptop by ChatGPT.


## Stage 4 — Separate customer-facing product experience

The **Customers → Customer portal preview** button now opens a visually distinct, full-width portal demonstration for the selected fictional organisation, rather than merely changing a heading in the operator console.

Features:
- Branded customer overview, sample security metrics, priority cases, and clearly inactive monitoring indicators.
- Customer-facing **Overview / Incidents / Services** navigation, with expandable sample incident summaries.
- Customer-only demo incidents based on the selected fictional tenant ID, using the `incidentsForDemoCustomer` fixture helper.
- An **Exit customer preview** action that returns to the SOC operator portfolio.
- Unit tests for the *demonstration* customer scoping helper.

**Critical:** this is a frontend display filter and a design preview. It is **not authentication, tenant isolation, authorisation, real security monitoring, or an operational customer portal**. No service can be purchased or activated from this demo. Production isolation must be enforced and independently tested in the backend and data access layer.

Update in VS Code (from `soctalk/frontend`): `cd ..`, `git pull --ff-only origin dev/rh-one`, `cd frontend`, `pnpm check`, `pnpm test:unit`. If Vite is already running it will usually reload automatically.

## Stage 5 — Response Centre (added)

The **Response Centre** is an operator-facing, **demonstration-only** response review module linked to the AI Analyst's existing in-memory investigation state.

- **Queue:** select a fictional case, see customer context and the preauthored recommended next step
- **Investigation gate:** before a demo review is possible, open the linked case in AI Analyst and run its *simulated* investigation
- **Decision gate:** record a proposed approval or rejection only after explicitly acknowledging that no real action will occur
- **Playbooks:** illustrative identity, endpoint, mailbox and firewall verification/approval steps, with no executable integrations
- **Decision log:** displays local browser-state decisions; deliberately **not** called an audit trail
- **Safety:** all execution counts are zero; no backend calls, no credentials, no device or account changes, no real approval or control enforcement

To test, use **Response Centre → select SEN-2048 → Open AI investigation → Run simulated investigation → Response Centre → check acknowledgement → Record proposed approval → Decision log**. The status should update when switching between the two screens. **Reset demo** returns all states to their starting values.

Run the same local checks as earlier from `soctalk/frontend`:

```powershell
cd ..
git pull --ff-only origin dev/rh-one
cd frontend
pnpm check
pnpm test:unit
```

Changes are committed to the development branch, but these checks must still be executed on the developer's laptop to verify compilation.


## Stage 6 — Detection Engineering & Monitoring Coverage

New **Detection Engineering** operator view, built entirely on synthetic data:

- **Rule library:** six example rule definitions with human-readable detection logic, assumed ATT&CK contexts, false-positive considerations, required data source, gaps and linked *demo* incidents.
- **Monitoring coverage:** six proposed telemetry sources (identity, endpoint, network, email, privilege audit and agent health) with explicit implementation gaps.
- **Test laboratory:** three synthetic scenarios per rule — matching, benign and incomplete data — evaluated by deterministic TypeScript predicates. Each test is intentionally small and is **not** production-quality detection logic.
- **Command Centre:** new coverage-quicklink into the Detection Engineering screen.
- **Incident navigation:** “View linked demo incident” opens the corresponding incident in the existing synthetic investigation queue.
- **Unit tests:** check all fixture outcomes, distinguish missing data from benign activity, validate source IDs and assert zero live monitoring.

All coverage metrics are **0 live rules, 0 connected sources, 0% verified live coverage**. Running a test never sends alerts, calls Wazuh, enables a rule, starts an agent or contacts an endpoint.

### Verification on your laptop

From \`soctalk/frontend\`:

\`\`\`powershell
cd ..
git status --short
git pull --ff-only origin dev/rh-one
cd frontend
pnpm check
pnpm test:unit
\`\`\`

If \`git status --short\` shows uncommitted work, preserve it before pulling. The local preview is still \`http://127.0.0.1:5173/sentry-preview\`. Refresh and open **Detection Engineering**. Validate:

1. Rule library search and filter.
2. “View linked demo incident” and return to Detection Engineering.
3. Monitoring coverage (all sources correctly marked **Not connected**).
4. Test laboratory for each rule: match, no match, missing data.
5. No real backend is required and existing SocTalk pages stay unchanged.

**Important:** GitHub commits have been verified. ChatGPT has not executed \`pnpm check\`, \`pnpm test:unit\`, or browser acceptance tests on the user's local computer. Confirm those before adding the next milestone.


## Stage 7 — SaaS security architecture preview

A new **Security Architecture** sidebar section illustrates the backend security model RH Sentry will need before real customers or telemetry are connected:

- **Access policy**: choose a fictitious actor, organisation and operation; see a deterministic example of allow/deny policy.
- **Response authorisation**: toggle example SOC lead and customer-admin approvals and test the dual-approval gate.
- **Data contracts**: view proposed identity, incident, response proposal and audit-event shapes, together with the missing backend implementation steps.
- **Policy tests**: missing sessions, inactive memberships, cross-customer access, platform-admin isolation, approvals, expiry and rejection scenarios.
- Detailed baseline: [RH_SENTRY_SECURITY_ARCHITECTURE.md](RH_SENTRY_SECURITY_ARCHITECTURE.md).

**These are only generic policy semantics and sample user interfaces, not production access controls.** Client-side decisions are never a security boundary. There is still no authenticated API, tenant-isolated database, secure audit service, SOC executor or connected identity provider. We cannot market the current prototype as secure SaaS.

For local verification run:

\`\`\`powershell
cd ..
git status --short
git pull --ff-only origin dev/rh-one
cd frontend
pnpm check
pnpm test:unit
\`\`\`

If \`git status --short\` shows changes, safeguard them before updating. In your local browser open \`http://127.0.0.1:5173/sentry-preview\`, choose **Security Architecture**, and test role/tenant denial plus both review toggles. These commands have **not yet been executed** on the user's laptop by ChatGPT.


## Stage 8 — Local-only authenticated API lab

A new **API Lab** sidebar screen connects *optionally* to a separate Python/FastAPI server running at \`http://127.0.0.1:8001\`. The original SocTalk backend is still unchanged. Details and Windows setup instructions: [dev/rh_sentry_lab_api/README.md](dev/rh_sentry_lab_api/README.md).

**Development features, fictional data only:**

- User must start the API and supply a temporary local password (no default credentials).
- Server-issued opaque HttpOnly cookies with one-hour expiry, same-site restriction and hashed session storage.
- Session-bound CSRF token on logout, fixed dev-origin CORS checks and explicit loopback binding.
- Five fictional identities with server-side membership lookup.
- SQLite-backed tenant-scoped incident list/detail reads; cross-tenant access returns 404.
- Persistent local journal of allowed and denied read operations; fictitious auditor can inspect it.
- Python tests for unauthenticated and cross-tenant denial, CSRF, local session revocation, records and audit persistence.

**Not implemented or claimed:** real IAM, MFA, production-strength sessions, tenant isolation for SocTalk's existing APIs, incident writes, tamper-resistant audit, real detection, live SIEM, AI inference or response execution. This sample service is **not deployable for paying customers**.

Test the Python module separately using \`python -m pytest -q tests\` within \`dev/rh_sentry_lab_api\`. The Svelte screen remains available without running the Python API; it will show that the API is offline. Frontend \`pnpm check\` and \`pnpm test:unit\` still need to run locally after pulling the branch. **No production deployment has been made.**


## Stage 9 — Persistent local incident management

The separate Python API Lab now supports server-authorised incident changes and analyst note records stored in local SQLite.

- **Server-side enforcement:** Only active analyst/lead memberships within the owning fictional organisation may change status or assignment or access internal analyst notes.
- **CSRF:** All incident mutations require the session-bound `X-CSRF-Token`, not just the logout action.
- **Concurrency and history:** Every successful change increments a case version, stores a history event and writes a lab audit record in one transaction. Stale versions are rejected with HTTP 409.
- **Evidence:** Plain-text analyst notes only, linked to tenant and incident. No URL attachments, file uploads, malware artefacts or executable response commands.
- **Frontend:** Select an incident in API Lab and open the case workspace. Customer viewers see a read-only summary; analysts can update and review note and change history.
- **Migration:** Existing fictional SQLite records are preserved when the new columns and tables are added.

Local API instructions and acceptance test sequence are in [dev/rh_sentry_lab_api/README.md](dev/rh_sentry_lab_api/README.md). **After pulling changes, stop and restart the running Python API** so it loads the updated server code. The frontend should hot-reload, but it can also be restarted if necessary.

GitHub Actions runs Python API tests and Svelte/TypeScript checks on the development branch. This is only a lab milestone; it does not imply production-grade authentication, encrypted customer storage, tamper-evident audit or independent penetration testing.

## Stage 10 — Local API cases in the main SOC workspaces

The **Incidents** and **AI Analyst** sections each have an explicit data-source switch:

- **Simulation:** the original interactive, hypothetical incident/AI-response demonstration remains unchanged. All sample graphs, customer portfolio, AI example reasoning and response prototypes continue to use browser-only fixtures.
- **Local API / SQLite:** a new tenant-scoped workspace reads fictional incident records from \`http://127.0.0.1:8001\`. The server validates the session and membership on each query; the UI never mixes these records into the simulated AI or Response Centre.
- **Incident management:** authorised sample analysts can change statuses, assign cases and write plain-text evidence notes using the existing server-enforced, CSRF-protected case editor.
- **AI Analyst in local mode:** this is deliberately titled **human analyst casework**. It shows the same persistent incident, stored notes and change history, but *does not invent AI findings* or route local records into the prewritten AI demo.
- **Cross-links:** a persistent case can be opened in the companion local incident/analyst workspace, preserving customer and case selection. Existing detection-rule links continue opening the independent simulation.
- **Session:** the CSRF token returned by an explicit login in **API Lab** lives only in the current Svelte preview page's memory. The token is handed to the main workspaces while the page remains mounted; it is never persisted to \`localStorage\` or included in a URL. After a full browser refresh, the cookie may remain valid for read-only viewing, but analyst edits require logging in again from **API Lab**.
- **No data leakage by fallback:** unauthenticated/expired sessions, offline API or unknown tenant membership show an explicit status rather than silently switching to simulated data.

### To try this milestone

Keep the separate Python backend running at port **8001** and the frontend at **5173**:

1. In VS Code, from the repo root run \`git status --short\` then \`git pull --ff-only origin dev/rh-one\` (preserve any uncommitted work before pulling).
2. Refresh the local Svelte preview at \`http://127.0.0.1:5173/sentry-preview\`. No Python/backend restart or schema migration is needed for this frontend-only milestone.
3. Open **API Lab**, log in as fictional \`alderwick-analyst\` with your existing temporary local password.
4. Open **Incidents → Local API / SQLite**. You should see exactly the authorised Alderwick cases, including the status and assignment you previously saved.
5. Open one case and select **Open analyst casework**. The AI Analyst section should show the same stored case, its evidence-note journal and case history. It must not claim that an AI model examined anything.
6. Return to **Incidents**. Log out in **API Lab**, then revisit local mode. Incident records should no longer load without an authenticated cookie.
7. Sign in as fictional \`alderwick-viewer\`; only a read-only case summary should appear. No local analyst-note access should be available.
8. Switch back to **Simulation** and confirm all original demo screens still work.

**Validation:** GitHub Actions ran \`pnpm check\` and the RH Sentry unit tests successfully on the development branch. Real browser navigation must still be exercised on the user's own laptop. No real client records or AI/SIEM services are connected.


## Stage 11 — Synthetic security-event pipeline

The **Event Pipeline** screen is a new operator-facing local lab for ingesting and inspecting carefully defined, fictional security events. It never accepts free-form log content and cannot connect a sensor or execute a response.

- Four predefined training scenarios are generated by the separate Python API.
- Server-issued cookie, CSRF token, active analyst membership and explicit tenant scope are required for event writes.
- Event provenance, source identifiers, UTC occurrence time, synthetic attributes and event/batch IDs are stored in local SQLite.
- Deterministic illustrative correlation results include rule IDs, explanations and the exact stored event IDs.
- A correlation links to an existing synthetic case only if it belongs to the selected tenant; **no automatic case creation, state change or evidence-write occurs**.
- Tenant-scoped idempotency prevents duplicate events when the same user submission is retried; a replay with a different scenario is rejected.
- Customer-viewer and cross-tenant reads/writes are denied. SQL results are constrained to the authorised tenant, and local test-data growth is capped at 50 batches per tenant.
- Benign sign-ins and missing-context scenarios yield no positive correlations. This is an example predicate lab, **not measured detection effectiveness**.

Backend tests run in GitHub Actions. Frontend preview checks run in a separate workflow. Local acceptance:

1. Pull \`dev/rh-one\` from the **soctalk root**, safeguarding any uncommitted work first.
2. **Restart the Python backend** in \`dev\rh_sentry_lab_api\` via Ctrl+C then \`.\.venv\Scripts\python.exe run.py\`; the existing SQLite file migrates without wiping previous records.
3. Keep Vite running on 127.0.0.1:5173.
4. In API Lab, sign in as the fictional \`alderwick-analyst\`.
5. Open **Event Pipeline**, choose *Unusual consecutive sign-ins*, and generate one batch. The lab should store two events, one example \`RHS-DET-001\` correlation, and a link to existing case \`SEN-2048\`.
6. Open that existing case in **Incidents → Local API / SQLite**. Confirm its version/status did not automatically change.
7. Return to Event Pipeline and run *Ordinary sign-ins* and *Incomplete sign-in telemetry*. Both should produce zero new correlations (earlier matches remain in the history).
8. Confirm viewer login and different-tenant access cannot read or submit the lab events.

This is the first stored example event pipeline, not live Wazuh ingestion, automated alerting, verified ATT&CK coverage or AI-driven analysis. No external network-facing backend is enabled.


## Stage 12 — Wazuh-compatible fictional alert parsing

In the existing **Event Pipeline** screen, two new generated, Wazuh-format training scenarios demonstrate the next step towards eventual SIEM integration:

- **Wazuh-format SSH failure burst:** three fictional alerts are constructed in the familiar Wazuh JSON structure. The strict adapter normalizes allowlisted timestamp/rule/agent/TEST-NET IP attributes, discarding untrusted raw logs and original fields. A demonstration correlation is attached to the generated events, with no automatic incident creation.
- **Wazuh-format single SSH failure:** one fictional alert with insufficient context; zero new synthetic correlations.
- All generated events use \`source=wazuh-format-synthetic-lab\`, not a live sensor source. The fabricated example rule \`100900\` is *not* an official rule identifier. Wazuh is neither installed nor contacted by this adapter.
- Existing backend isolation, CSRF checks, local SQLite persistence, analyst roles, idempotent submission and audit events are reused unchanged.
- Adapter unit/API tests exercise the Wazuh-format sample, malformed fields, unsafe raw-log omission, incorrect IPs, cross-tenant access, replay and case immutability.

**Local setup:** Pull \`dev/rh-one\`, keep Vite on 127.0.0.1:5173, and restart the Python server at 127.0.0.1:8001. Log in as \`alderwick-analyst\` through API Lab. Open Event Pipeline and try both new scenarios. Backend test details and 16 GB laptop hardware considerations are in [dev/rh_sentry_lab_api/README.md](dev/rh_sentry_lab_api/README.md).

A **real** Wazuh manager, indexer or agent is not connected; integration using genuine test alerts requires a separate trusted collector and VM setup. All platform functionality remains development-only, with zero production monitoring.

## Stage 13 — Wazuh offline replay and VirtualBox readiness

**Implemented:** \`dev/rh_sentry_lab_api/wazuh_replay.py\`, a read-only local validator for intentionally fictional, Wazuh-formatted JSONL records. It enforces strict TEST-NET/fictional hostname constraints, field allowlisting, size/record limits, event-ID uniqueness and a conservative five-minute three-alert SSH correlation. A sample fixture and pytest tests validate its fail-closed behaviour.

**Not implemented:** a Wazuh VM, agent registration, a live collector, live event ingestion, production credential handling, or any RH Sentry real-time SIEM integration. The current Event Pipeline remains synthetic.

**Next external dependency:** follow [RH_SENTRY_WAZUH_LAB_PLAN.md](RH_SENTRY_WAZUH_LAB_PLAN.md) to decide whether the user's 16 GB laptop can safely support an isolated Wazuh VM without Kali running. Do not introduce genuine telemetry before a private repository and trusted-collector controls exist.

Local test command (from \`dev\rh_sentry_lab_api\`): \`.\.venv\Scripts\python.exe wazuh_replay.py --file fixtures/wazuh_training_ssh.jsonl\`. This change adds no frontend controls and requires no Python service restart.

## Stage 14 — Software-first architecture and SQLite-backed Command Centre

**Development decision:** VirtualBox, Wazuh and Kali are reserved for final end-to-end integration tests *after* the SOC software, security boundaries, persistent data models, services and synthetic test harness are built. See the full [RH Sentry software-first build roadmap](RH_SENTRY_BUILD_ROADMAP.md).

The **Command Centre** now supports the same explicit **Simulation / Local API / SQLite** switch as Incidents and AI Analyst.

- Simulation preserves the original fictional Command Centre appearance and charts. Its counts remain demonstration figures.
- Local API / SQLite loads the tenant-specific **\`GET /api/tenants/{tenantId}/lab/overview\`** endpoint from the isolated Python service. The API checks the authenticated user's active tenant membership before querying incident totals, open critical/high cases, assignments, status distribution and the latest five cases.
- Local mode uses actual *stored fictional* incident and synthetic event counts; no illustrative chart or cross-tenant record is silently merged into those results.
- Fictional customer viewers see their permitted incident summary but receive \`null\` for internal synthetic event and correlation totals, rather than the analyst-only details.
- Live sensors and live coverage remain **zero**, AI inference remains disconnected. These are not genuine customer metrics.
- Recent case links open the authorised **Incidents → Local API / SQLite** workspace, preserving the same fictional tenant and case.
- If the Python API is offline or login has expired, the local Command Centre fails closed with a visible prompt to use API Lab; it never substitutes simulation values as real readings.

**Local acceptance:** Pull the \`dev/rh-one\` branch, restart the Python API (new read endpoint) at 127.0.0.1:8001, and keep Vite on 127.0.0.1:5173. Log in via API Lab as fictional \`alderwick-analyst\`. Open **Command Centre → Local API / SQLite**, compare the status/assignment counts against Incidents, and generate a synthetic batch in Event Pipeline to verify the event counts update when refreshed. Sign out and check that data disappears on a fresh view. Select **Simulation** to confirm the original dashboard still works.

Backend tenant isolation/metrics tests and Svelte/frontend unit checks run in GitHub Actions. Browser interaction still requires the user's own local acceptance test. **No production deployment and no VM connection were performed.**

## Stage 15 — Tenant-scoped persistent Asset Management

The Assets section now has Simulation and Local API / SQLite modes. The existing visual demonstration is preserved. The local mode retrieves registered fictional systems through the authenticated backend and supports analyst-only asset registration/updates, criticality and lifecycle, case associations and audit history.

The new asset API is scoped to customer membership in server-side SQL. Mutations require analyst/lead role, CSRF, strict field validation and optimistic concurrency. Asset–incident associations use tenant-constrained composite database foreign keys. Read-only customer viewers cannot see internal asset change history or modify records. An intentionally removed seed link will not return after a Python restart.

No asset is genuinely monitored: connected sensor counts stay at 0, monitoringState is not_connected, lastSeen is null, and no product feature claims agent status or risk assurance. Registered asset totals are exposed separately in Command Centre → Local API / SQLite.

**Local acceptance:** Pull dev/rh-one; restart only Python API (new database tables/endpoints); keep Vite running; sign in through API Lab as fictional alderwick-analyst. In Assets → Local API / SQLite, inspect seeded customer-owned assets, open a linked incident, register a fictional training asset, edit it, link/unlink a case, and verify changes persist after refresh. Then sign in as a customer viewer to confirm read-only access. See dev/rh_sentry_lab_api/README.md for exact routes.

Backend and frontend automation has passed; direct interaction still requires a browser check on the developer's laptop. VirtualBox/Wazuh remains the final integration stage after core SOC software and security infrastructure are implemented.

## Stage 16 — Persistent synthetic Detection Engineering

The Detection Engineering page now supports **Simulation / Local API / SQLite**. The existing static visual rule demonstration is preserved. Local mode exposes a tenant-scoped, authenticated rule catalogue, versioned rule edits, synthetic test-batch picker, historical test runs, matched event provenance, false-positive disposition and analyst review journal.

The deterministic rule strategies are intentionally allowlisted: fictional impossible-travel sign-ins, encoded PowerShell with an untrusted parent, and Wazuh-format training SSH failure bursts. No arbitrary query evaluation, raw live events, AI inference or agent commands are accepted. All tests are **manual** against existing stored synthetic event batches; a positive result is a review-only training finding, never an automatically created incident.

**Local acceptance:** Pull dev/rh-one, restart Python API to migrate new SQLite tables (existing fictional cases/assets preserved), keep Vite running. Sign in through API Lab as alderwick-analyst, ingest a synthetic impossible-travel batch in Event Pipeline, open Detection Engineering → Local API / SQLite, select RHS-DET-001 and the new batch, then run a synthetic test. Expect a matched outcome with two supporting event IDs and one unreviewed finding. Record a false-positive disposition with a reason, refresh and verify the review persists. Verify ordinary-signins gives no positive finding; a customer viewer cannot access internal rules. The original Simulation mode remains available.

The Assets page's **+ Register Asset** action has been moved to its upper toolbar, with the form placed immediately below the tenant selector. No production deployment or VirtualBox activity occurred.

## Future phases (not implemented yet)

1. Refine the RH Sentry interface and approved brand assets.
2. Create typed, provider-neutral contracts for incidents, detections, assets and response approvals.
3. Connect SocTalk FastAPI to the UI, with real authentication, authorisation, tenancy and audit controls.
4. Integrate Wazuh ingestion and a tested AI investigation engine in an isolated environment.
5. Validate detection efficacy, response safety, resilience, tenant isolation, and regulatory requirements before any pilot.

The prototype is not a commercially ready SOC.
