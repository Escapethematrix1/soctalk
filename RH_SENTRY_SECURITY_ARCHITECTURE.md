# RH Sentry — SaaS security architecture baseline

**Status:** design baseline only; not deployed or security-approved.  
**Location:** the public development fork contains only generic contracts, fictional identities and policy examples. Do not put the proprietary RH Sentry engine, secrets, real tenant data or private threat intelligence in this repository.  
**Product separation:** RH Sentry is the proposed AI SOC product. Red Horizon One remains a different client platform.

## 1. Fundamental boundaries

Security must be enforced by a trusted backend and data store. The SvelteKit **\`/sentry-preview\`** interface is a local demo with fabricated data; selecting an organisation or a role there cannot constitute authentication, authorisation or tenant isolation.

For each request:

1. Authenticate using a server-verified session, not a client-supplied actor ID or role.
2. Resolve active membership in the **requested tenant** and permission from the authoritative membership store.
3. Enforce tenant scope on the data query, writes, counts, search, bulk operations, exports, background jobs and event subscriptions.
4. Do not return another tenant's metadata, record counts, error details or cached query results.
5. Record allow/deny decisions using server-generated audit identifiers and timestamps.
6. Recheck permissions at the point of any potentially disruptive response action.

The \`frontend/src/lib/sentry-contracts/\` folder defines example DTOs and pure TypeScript policy semantics to guide discussion. **It is not a security implementation** and cannot replace backend enforcement.

## 2. Proposed service boundaries

\`\`\`text
Customer browser / RH Sentry operator browser
       |
       | TLS; secure, HttpOnly, SameSite cookies; CSRF protection
       v
Authentication + application API
       |
       +-- Identity and tenant-membership service
       +-- Incident & investigation service -----> tenant-keyed transactional database
       +-- Detection engineering catalogue ------> versioned rule store
       +-- Secure audit-event writer ------------> append-only, access-controlled audit store
       +-- Approval & response coordinator ------> isolated execution service (future)
       |
       +-- Telemetry connector service ----------> Wazuh / other sources (future)
       +-- AI investigation service -------------> evidence-grounded model calls (future)
\`\`\`

All inter-service calls must carry authenticated, authorised tenant context and validate object ownership. Tenant IDs in JSON bodies and query strings are never trusted as proof of authority.

## 3. Roles (proposed, not approved)

| Role | Intended permissions | Security limit |
| --- | --- | --- |
| Customer viewer | Read own incidents, assets and reports | Cannot approve response or manage monitoring |
| Customer administrator | Customer reads plus scoped approval and member administration | Cannot write detection rules |
| SOC analyst | Assigned-tenant reads, rule reads, response proposals | Cannot approve own proposed actions |
| SOC lead | Assigned-tenant reads, rule management and review | Does not automatically obtain access to every tenant |
| Platform administrator | Organisation metadata administration | No automatic read access to incident content |

A true service may require additional roles, delegated customer permissions, emergency access, service principals and stronger restrictions. An emergency/break-glass access path must have explicit approval, a bounded lifetime and detailed audit.

## 4. Tenant data model

At minimum every tenant-owned resource should have an immutable owner tenant ID. Proposed domain entities:

- \`tenants\`: ID, status, service plan and managed coverage configuration
- \`identities\`: external identity-provider identifier, status and login metadata
- \`memberships\`: composite tenant/identity reference, role, state and authorisation version
- \`assets\`: tenant ID, external asset mapping, source, heartbeat and last-seen status
- \`incidents\`: tenant ID, case state, evidence references, timestamps and assignee
- \`events\`: tenant ID, source, ingest time, event time, integrity status and retention class
- \`rule_versions\`: tenant ID or globally governed rule scope, immutable version and testing evidence
- \`response_proposals\`: tenant ID, incident, exact action type and target, proposer, expiry
- \`response_decisions\`: tenant ID, proposal ID, reviewer, signature/identity evidence, decision
- \`audit_events\`: immutable server timestamp, actor, tenant, permission, outcome and trace ID

Recommended invariants: composite unique constraints for memberships, foreign keys ensuring child records refer to the same tenant, indexes beginning with tenant ID on tenant-scoped queries, and policies blocking cross-tenant reads/writes. Database row-level security can be a defence-in-depth layer but must be tested with correct session context and not relied upon alone.

## 5. Authorisation & response approval invariants

- Default **deny** for unknown actor, inactive session, unknown tenant, inactive membership or unsupported permission.
- Platform administration does not imply customer-incident access.
- Every sensitive operation must have a narrow object and tenant scope.
- Approvals must be bound to an immutable proposal revision and exact target/action; no stale approval may be replayed after a material change.
- The proposer cannot approve their own disruptive action.
- Require authorised SOC and customer-side approvers in the example policy; any emergency exception needs its own explicit contract and test plan.
- Reject, expiry, membership revocation, policy changes or tenant suspension must block execution.
- Execute only after a fresh trusted check; use idempotency keys, retries with bounds and rollback/compensation plans.
- Record every stage in persistent, tamper-evident audit history.

The preview \`checkDemoProposalReadiness\` function is a small policy illustration. Its \`ready\` result is **not an execution authorisation**. No executor is implemented.

## 6. Authentication & session security

Before opening RH Sentry to outside users:

- Use a supported OIDC identity provider, rotating signing keys and MFA enforcement appropriate to role.
- Secure, HttpOnly and SameSite cookies; server-side session invalidation; short-lived privileged sessions.
- CSRF protections for state changes and strict CORS allowlists.
- Server-side permission checks on every route, background task, WebSocket/SSE subscription and export.
- Rate limiting, secure password/reset/invitation flows, verified email ownership and strong recovery controls.
- Security headers, CSP, input validation, safe logging, dependency scanning and secrets management.
- Tenant isolation penetration tests, including cross-tenant IDs, alternate filters, counts, exports, jobs, caching and realtime notifications.

## 7. AI investigation design constraints

AI output is untrusted analysis, not authority. All claims must cite stored tenant-scoped evidence, include time/source provenance and express missing information. The model must not receive other tenants' data, must not be able to invoke destructive tools without external enforcement, and must be tested for prompt injection in log content, false-confidence claims, data exfiltration and unsafe proposed actions.

## 8. Local backend foundation: implemented as a lab only

A standalone, optional development service now lives at [dev/rh_sentry_lab_api](dev/rh_sentry_lab_api/README.md).

- FastAPI listens on localhost port 8001 using a fixed loopback launcher.
- Fictional user sessions, tenant memberships, incident records and request journals are stored locally.
- Tenant-owned incidents are queried server-side with the tenant ID in SQL.
- No trusted identity comes from a request body or a client-chosen role.
- Unit/integration tests demonstrate 401 unauthenticated, 404 cross-tenant reads, CSRF logout and SQLite persistence.
- A dedicated read-only GitHub Actions workflow runs the Python API tests.

**Do not interpret this proof-of-concept as production implementation of the earlier architectural requirements.** The lab uses a temporary shared developer password across sample accounts, local HTTP cookies, a small SQLite database and no production IdP. It has no privileged response executors, no real customers and no telemetry. Its test suite is narrower than an independent security review.

The production feature roadmap below remains outstanding and should be implemented in Red Horizon's own private repository.

## 9. Suggested production implementation order (not begun)

1. Move product-specific work to a private repository under Red Horizon's control.
2. Choose real identity provider and database topology. Finalise schemas and API permissions before wiring any live data.
3. Build a thin, authenticated backend with tenant-scoped list/read endpoints and a test database seeded only with synthetic tenants.
4. Add server-side denial/allow audit and thorough cross-tenant integration tests.
5. Implement response proposals and reviews **without** an executor; test revoked/expired access and concurrency.
6. Integrate Wazuh in an isolated lab and measure ingestion correctness and alert attribution.
7. Add evidence-grounded AI investigation behind strictly scoped retrieval, with human review.
8. After threat modelling, security testing, performance tests, data-retention policy, DPA/subprocessor review and incident-management runbooks, decide whether a controlled pilot is appropriate.

**No production deployments, customers or live credentials are touched by this document.**
