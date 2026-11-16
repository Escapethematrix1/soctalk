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

## Future phases (not implemented yet)

1. Refine the RH Sentry interface and approved brand assets.
2. Create typed, provider-neutral contracts for incidents, detections, assets and response approvals.
3. Connect SocTalk FastAPI to the UI, with real authentication, authorisation, tenancy and audit controls.
4. Integrate Wazuh ingestion and a tested AI investigation engine in an isolated environment.
5. Validate detection efficacy, response safety, resilience, tenant isolation, and regulatory requirements before any pilot.

The prototype is not a commercially ready SOC.
