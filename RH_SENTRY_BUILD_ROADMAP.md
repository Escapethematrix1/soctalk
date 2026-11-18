# RH Sentry — complete software-first build plan

**Product:** RH Sentry, defensive SOC SaaS under Red Horizon Cyber Group.
**Build principle (agreed 17 November 2026):** **VirtualBox, Wazuh, Kali and live test sensors are final end-to-end acceptance tools**, not prerequisites for building the application. Complete the product's software architecture and test it using fictional event fixtures, deterministic test feeds, contract tests and isolated CI first.

**Current status:** substantial local *prototype*; not a production SOC, not multi-customer SaaS-ready, no AI provider connected, no real customer data or live monitoring. Code is presently on \`Escapethematrix1/soctalk\` branch \`dev/rh-one\`. The original SocTalk platform and production deployments remain untouched.

## Development gates

Each gate requires reviewable UI, documented API/database contracts, automated unit/integration tests and recorded acceptance criteria. All backend read/write routes must enforce tenant ownership server-side, and state-changing routes must require authenticated roles, validation and CSRF (or appropriate secure service-to-service authentication). **Never treat UI filtering as an access-control boundary.**

| Gate | Scope | Current status | Finish criterion |
|---|---|---|---|
| 0. Isolated prototype | Visual design, fictional tenants, initial sessions, incident status/assignment/notes and SQLite persistence | Demonstrated locally | Preserve as a regression baseline; keep source under controlled development branch |
| 1. Command Centre | Actual persisted fictional case counts, recent incidents, zero-live coverage/health messaging, tenant-selected dashboard | **Local SQLite mode implemented** | Browser acceptance, verified session expiry and no cross-tenant reads |
| 2. Asset inventory | Stored tenant-owned assets, ownership, lifecycle, investigation links and explicit sensor status | **Local SQLite prototype implemented; browser acceptance pending; software/risk evidence not implemented** | CRUD, import validation, cross-tenant tests, honest sensor-health and asset provenance |
| 3. Detection engineering | Versioned, approved rule catalogue, event schema, fixture runner, correlation results, false-positive handling | **Local SQLite rule catalogue, manual batch evaluations and finding review implemented; browser acceptance pending** | Complete lifecycle approval/rollback, verified event quality, performance, and downstream case links without unapproved execution |
| 4. Trusted telemetry contract | Immutable source provenance, authenticated service/tenant mapping, deduplication, ingest batching, retry queues, retention | *Offline fictional parsers only* | Synthetic event collector and back-pressure exercised in isolated integration tests; **no VM yet** |
| 5. Incident/evidence operations | Case intake, state machine, severity, assignment, notes, case/evidence chain-of-custody, search, escalations | Basic SQLite local lab works | Persistent approvals, tenant-safe evidence, concurrent writes, governance and audit tests |
| 6. Analyst/AI reasoning | Evidence retrieval, constrained prompts, model abstraction, explainable findings, uncertainty and human review | Pre-authored AI demo; **no actual model** | Structured evaluation on synthetic investigations, prompt-injection tests, clear provenance, no autonomous action |
| 7. Response Centre | Playbook registry, proposals, approvals, simulation receipts, explicit separation of duties | **Local SQLite workflow implemented; browser acceptance pending; no real executor** | End-to-end operator acceptance, escalation/rollback planning and production-grade signed approvals before real integration |
| 8. Reporting/customer portal | Persistent tenant scoped dashboards, executive and technical reports, customer permissions, export redaction | Demo reporting and customer portfolio | Cross-tenant/report export tests; downloadable signed-off reports and data minimisation |
| 9. SaaS platform foundation | Private Red Horizon repository, build pipeline, production IAM/MFA, session management, tenant DB enforcement, audit logging, backup/restore, monitoring/observability | Early role demo and lab-only shared-password auth | External security review, independent tenant isolation penetration tests, recovery drills |
| 10. Final system integration | Isolated Wazuh appliance in VirtualBox, synthetic agent traffic, trusted collector, end-to-end investigation, outage/performance tests | **Not started by design** | Verified Wazuh→collector→rule→incident→analyst→report flow, zero cross-tenant leakage |
| 11. Commercial pilot/release | Pricing/licensing, SLAs, legal/compliance, privacy, operations, SOC staffing and incident coverage | Not ready | Controlled pilot, informed customer agreements, release/rollback readiness |

## Implementation order

1. **Finish isolated application software** using the fake data generator and Python test backend. Prioritize assets, detection rules, incident operations, human analyst workbench and reports so the product can be exercised without an SIEM.
2. **Introduce proper platform boundaries** before any sensitive/company-owned data: move proprietary development to a private repository; implement database migration strategy, production-grade sessions/IAM, RBAC, tenanted persistence, retention and encrypted configuration.
3. **Establish reliable internal services** with synthetic queues/events: authentication and ingest identity, schema versioning, replay/idempotency controls, retries, dead-letter handling, latency/error telemetry and health endpoints. Complete performance/security tests without VirtualBox.
4. **Validate AI reasoning** against curated, invented investigations. An AI UI is not an AI engine. Require evidence citations and fail safely when the model is offline or uncertain; operators approve every proposed disruptive action.
5. **Build deployment and operational readiness**, including private CI, SAST/dependency auditing, infrastructure as code, rollback, DR backup/restore, incident logging and a staged environment. No production or client deployment before verification.
6. **Only then configure VirtualBox/Wazuh**, connecting a lab sensor via a mutually authenticated collector. Test source provenance, incident correctness, agent downtime, queue back-pressure, tenant segmentation and response no-op/dry-run behavior. Preserve the Windows host's 16 GB RAM budget by running only the necessary VM(s).

## Explicit safety/product constraints

- RH Sentry is **not Red Horizon One**. The latter is the planned client SaaS portal; avoid name collision.
- Never merge simulated alerts with authentic agent events without a strong source indicator. Make synthetic, test and live fields explicit in both APIs and UI.
- Real-time monitoring means staff, triage SLAs, audit, availability and escalation—not just a running dashboard. Do not advertise 24/7 SOC coverage until operationally staffed and verified.
- Do not implement unsafe or automatic endpoint actions as part of prototype demos. Real response execution needs least privilege, change windows, auditable approvals and scoped policies.
- No genuine user/company passwords, production logs, client identifiers, personal data or proprietary secrets in the public SocTalk fork.
- Maintain the approved RH Sentry wordmark: **red R**, white H/SENTRY, red dot; small overline **RED HORIZON CYBER GROUP**; independently scrollable left sidebar.
- Development remains local and low-cost, but a zero-budget prototype does not imply zero production hosting, people, insurance or compliance expense.
- Do not infer VirtualBox access or a deployed Wazuh manager from passing format-parser tests.

## Current milestone check

The first Command Centre local view is backed by \`GET /api/tenants/{tenantId}/lab/overview\` on the localhost Python API. It aggregates existing case data and analyst-visible synthetic event totals in SQL with the authenticated tenant scope. Customer viewers receive no analyst-only event counts; all live coverage stays explicitly zero. The original Command Centre simulation is still present and is not overwritten.

**Browser acceptance:** pull \`dev/rh-one\`, restart the Python API at 127.0.0.1:8001 (new endpoint), leave Vite at 127.0.0.1:5173, log in via API Lab, select **Command Centre → Local API / SQLite**. Confirm persisted incident statuses and count changes, 0 live sensors and cross-tenant protection. Then select **Simulation** to verify the original page. Add a fictional Wazuh-format event in Event Pipeline and refresh to see the stored synthetic total change.

## When to involve the VM

Only after software gates 1–9 are accepted should \`RH_SENTRY_WAZUH_LAB_PLAN.md\` be executed. The VM exists to validate a built integration, *not* to compensate for missing core SOC services.

### Gate 2 progress: persistent asset inventory

The Assets section now supports Simulation and Local API / SQLite modes. The backend stores tenant-owned fictional systems with type, environment, owner, criticality, lifecycle, record version, incident associations and a change journal. Analysts can create and edit records or link/unlink incidents, while customer viewers can only read. Tenant-scoped endpoints, composite foreign keys, CSRF and stale-version checks protect the local lab.

Every asset reports monitoringState=not_connected, lastSeen=null and zero connected sensors. **Registration is not monitoring or security coverage.** The Command Centre reports registered assets separately from actual live sensors, which remain zero.

Python backend tests and Svelte frontend checks passed in GitHub Actions. Browser acceptance is still needed; software bill of materials, vulnerability exposure and authentic agent attestation remain future work.

### Gate 3 progress: persisted synthetic Detection Engineering

Detection Engineering now offers explicit Simulation / Local API / SQLite modes. In local mode, fictional SOC analysts can create and version safe rule drafts from exactly three allowlisted strategies, tune bounded thresholds, change test status and inspect an immutable version history. No scripts, search queries or arbitrary user-supplied event data can run.

Rule tests evaluate existing tenant-owned synthetic event batches deterministically. Each persisted test stores a version/threshold snapshot and supporting event IDs. Positive evaluations create fictional **findings for human review**, not incidents, security alerts, notifications, or endpoint actions. Human reviews can mark a finding false positive or needing investigation, with a reason and versioned history. No AI provider or Wazuh service is involved.

All rule internals are SOC-analyst-only and all writes are CSRF protected. Strict server-side tenant checking, composite database foreign keys, idempotency, input validation and audit entries are tested. The rule test repository has a finite 100-test-per-tenant local cap; these controls are laboratory safeguards, not enterprise-scale readiness.

The Assets control to **Register Asset** also moved to the header, and the registration form now opens immediately beneath the authorised tenant selector.

**Still outstanding:** browser acceptance; production IAM and deployment; real source/tenant attestation; detection efficacy testing; rule lifecycle governance; full case management from findings; alerts and notification delivery; reliable telemetry queues; operational human response workflows. Wazuh/VirtualBox remains deferred to the final integration stage.


### Gate 7 progress: streamlined Response Centre and platform navigation (18 November 2026)

**Operator simplicity is now a product requirement** rather than a cosmetic preference:

- Sidebar prioritises five core sections (Command Centre, Incidents, Response Centre, Assets and Reports). The six technical/admin sections live behind an explicit **Advanced tools** toggle, retaining access without clutter.
- The page header now recommends one context-aware **Next** action, rather than showing an unrelated report action and demonstration alert injection on every page. Simulation injection remains only on the Command Centre design demo.
- After a successful local API sign-in, RH Sentry selects persisted fictional-data mode by default; it does not silently fall back to simulation on sign-out.
- **Find a feature** is a compact global, searchable task guide. A single reviewed catalogue at \`frontend/src/lib/sentry-contracts/platform-guide.ts\` defines all eleven destinations, real navigation steps, common search terms, next actions and analyst access warnings. The guide navigates to real UI views and clearly labels features not yet connected.
- The future AI Analyst should read from this catalogue via an authorised navigation/retrieval service, confirm role/tenant permissions and give exact, version-aware destinations. It must **never invent page locations** or mistake a planned feature for an available one. Current help is **deterministic, not AI-powered**.

The Response Centre now has **Simulation / Local API / SQLite** modes. The local version is a deliberately focused workflow:

1. Analyst proposes an action against a tenant-owned, fictional incident using one of four non-executable playbooks.
2. A **different** authorised SOC lead approves the **dry-run only** or rejects it, with a mandatory explanation.
3. A lead may record an idempotent dry-run receipt. The backend has **no endpoint, account, shell, browser automation, network or notification executor** and reports zero external actions.

All request histories and receipts persist in SQLite with authenticated, tenant-scoped queries, CSRF for writes, version checks, auditing, finite lab limits and tested separation of duties. Customer viewers cannot access the response queue. An approval is never equivalent to authorisation for a real system action. This is **local laboratory workflow only**, not a commercial SOC playbook engine.

**Outstanding:** browser acceptance, production IAM, timeout handling, per-customer roles/approval policies, response SLAs, escalation, playbook efficacy tests, richer audit integrity, signed approvals, reconciliation, rollback plans, case evidence handoff and connected response integrations. VirtualBox/Wazuh stays last for final E2E acceptance.
