<script lang="ts">
	import {
		checkScopedAccess,
		checkDemoProposalReadiness,
		rolePermissions
	} from '$lib/sentry-contracts/policy';
	import type {
		IdentityContext,
		SentryPermission,
		SentryResponseProposal,
		SentryReviewDecision
	} from '$lib/sentry-contracts/types';
	import { demoCustomers } from '$lib/sentry-demo/customer';

	type Screen = 'Access policy' | 'Response authorisation' | 'Data contracts';
	const screens: Screen[] = ['Access policy', 'Response authorisation', 'Data contracts'];
	const identities: IdentityContext[] = [
		{ actorId: 'analyst-1', active: true, platformRole: 'none', memberships: [{ tenantId: 'alderwick', role: 'soc_analyst', active: true }] },
		{ actorId: 'lead-1', active: true, platformRole: 'none', memberships: [{ tenantId: 'alderwick', role: 'soc_lead', active: true }] },
		{ actorId: 'customer-1', active: true, platformRole: 'none', memberships: [{ tenantId: 'alderwick', role: 'customer_admin', active: true }] },
		{ actorId: 'viewer-1', active: true, platformRole: 'none', memberships: [{ tenantId: 'alderwick', role: 'customer_viewer', active: true }] },
		{ actorId: 'summit-analyst', active: true, platformRole: 'none', memberships: [{ tenantId: 'summit', role: 'soc_analyst', active: true }] },
		{ actorId: 'platform-operator', active: true, platformRole: 'platform_admin', memberships: [] },
		{ actorId: 'suspended-analyst', active: false, platformRole: 'none', memberships: [{ tenantId: 'alderwick', role: 'soc_lead', active: true }] }
	];
	const actorLabels: Record<string,string> = {
		'analyst-1': 'SOC analyst · Alderwick',
		'lead-1': 'SOC lead · Alderwick',
		'customer-1': 'Customer administrator · Alderwick',
		'viewer-1': 'Customer viewer · Alderwick',
		'summit-analyst': 'SOC analyst · Summit',
		'platform-operator': 'Platform administrator · no tenant access',
		'suspended-analyst': 'Suspended SOC lead · Alderwick'
	};
	const permissions: SentryPermission[] = [
		'incidents:read', 'assets:read', 'reports:read',
		'rules:read', 'rules:write', 'responses:propose',
		'responses:approve', 'members:manage', 'tenants:list'
	];
	const proposal: SentryResponseProposal = {
		id: 'SEN-DEMO-RESP-01', tenantId: 'alderwick', incidentId: 'SEN-2048',
		proposedBy: 'analyst-1', actionType: 'revoke_sessions', targetResourceId: 'DEMO-IDENTITY-01',
		justification: 'Demonstration sign-in anomaly that would require confirmation.',
		createdAt: '2026-11-16T10:00:00.000Z', expiresAt: '2026-11-16T12:00:00.000Z'
	};
	const fixedNow = '2026-11-16T11:00:00.000Z';
	const decision = (actorId: string, kind: 'approve' | 'reject'): SentryReviewDecision => ({
		proposalId: proposal.id, tenantId: proposal.tenantId, actorId, decision: kind,
		occurredAt: '2026-11-16T10:30:00.000Z'
	});
	const roleNames = ['customer_viewer', 'customer_admin', 'soc_analyst', 'soc_lead'] as const;
	let screen: Screen = 'Access policy';
	let actorId = 'analyst-1';
	let tenantId = 'alderwick';
	let permission: SentryPermission = 'incidents:read';
	let socApproved = false;
	let customerApproved = false;
	let rejected = false;

	$: actor = identities.find((entry) => entry.actorId === actorId) ?? identities[0];
	$: policy = checkScopedAccess(actor, tenantId || null, permission);
	$: reviewDecisions = [
		...(socApproved ? [decision('lead-1', 'approve')] : []),
		...(customerApproved ? [decision('customer-1', 'approve')] : []),
		...(rejected ? [decision('customer-1', 'reject')] : [])
	];
	$: readiness = checkDemoProposalReadiness(proposal, reviewDecisions, identities, fixedNow);
</script>

<div class="security-architecture">
	<div class="warning"><span class="warn-symbol" aria-hidden="true">◇</span><div><strong>Security architecture preview — not active security</strong><p>All roles, identities and authorisations below are fictional, local demonstrations. Actual authentication, database scoping, response approvals and audit integrity require independently tested backend enforcement.</p></div><span class="offline">NO AUTH BACKEND</span></div>
	<div class="stats">
		<div><span>VERIFIED AUTH SESSIONS</span><strong>00</strong><small>No identity provider connected</small></div>
		<div><span>PROTECTED CUSTOMER TENANTS</span><strong>00</strong><small>No server-side isolation yet</small></div>
		<div><span>PERSISTENT AUDIT EVENTS</span><strong>00</strong><small>No secure audit store</small></div>
		<div><span>RESPONSE EXECUTORS</span><strong>00</strong><small>No external actions available</small></div>
	</div>
	<div class="tabs" aria-label="SaaS architecture sections">{#each screens as item}<button type="button" class:active={screen === item} aria-pressed={screen === item} on:click={() => (screen = item)}>{item}</button>{/each}</div>

	{#if screen === 'Access policy'}
		<div class="access-grid">
			<section class="panel controls">
				<div class="panel-heading"><span class="eyebrow">AUTHORISATION MODEL / DEMO</span><h2>Evaluate a request</h2><p>Change the example identity, target organisation and operation to see the proposed deny-by-default policy.</p></div>
				<div class="control">
					<label for="sentry-actor">DEMONSTRATION IDENTITY</label>
					<select id="sentry-actor" bind:value={actorId}>{#each identities as item}<option value={item.actorId}>{actorLabels[item.actorId]}</option>{/each}</select>
				</div>
				<div class="control">
					<label for="sentry-tenant">REQUESTED TENANT</label>
					<select id="sentry-tenant" bind:value={tenantId}><option value="">No tenant specified</option>{#each demoCustomers as customer}<option value={customer.id}>{customer.name}</option>{/each}</select>
				</div>
				<div class="control">
					<label for="sentry-permission">REQUESTED OPERATION</label>
					<select id="sentry-permission" bind:value={permission}>{#each permissions as item}<option value={item}>{item}</option>{/each}</select>
				</div>
				<div class="request-card"><span class="eyebrow">EXAMPLE RESOURCE REQUEST</span><code>{actor.actorId}</code><code>{tenantId || 'NO TENANT'}</code><code>{permission}</code></div>
			</section>

			<section class="panel decision">
				<div class="panel-heading"><span class="eyebrow">POLICY EVALUATION / PURE FUNCTION</span><h2>Access decision</h2></div>
				<div class="decision-result" class:permitted={policy.allowed}>
					<span>EXAMPLE POLICY RESULT</span>
					<h3>{policy.allowed ? 'Allowed in model' : 'Denied in model'}</h3>
					<p>{policy.reason}</p>
				</div>
				<div class="explain"><span class="eyebrow">WHAT THIS TEST DOES</span><p>It evaluates a simple TypeScript function using fabricated role memberships. It does not open customer records, establish a session, send requests or grant anyone permissions.</p></div>
				<div class="guarantees">
					<div><span>01</span><strong>Explicit tenant required</strong><p>A missing or unknown tenant scope fails closed.</p></div>
					<div><span>02</span><strong>Active membership checked</strong><p>Cross-organisation access cannot be inferred from the selected UI view.</p></div>
					<div><span>03</span><strong>Platform role is not a data bypass</strong><p>Listing organisation metadata does not automatically permit reading tenant incidents.</p></div>
				</div>
			</section>
		</div>
		<div class="panel matrix">
			<div class="panel-heading"><span class="eyebrow">ILLUSTRATIVE ROLE MATRIX</span><h2>Minimum required privileges</h2><p>This is a proposed starting policy, not a final contractual permissions model.</p></div>
			<div class="table-scroll"><table><thead><tr><th>Permission</th>{#each roleNames as role}<th>{role.replaceAll('_', ' ')}</th>{/each}</tr></thead><tbody>{#each permissions.filter((value) => value !== 'tenants:list') as action}<tr><td><code>{action}</code></td>{#each roleNames as role}<td><span class:yes={rolePermissions[role].includes(action)}>{rolePermissions[role].includes(action) ? '✓' : '—'}</span></td>{/each}</tr>{/each}</tbody></table></div>
		</div>
	{:else if screen === 'Response authorisation'}
		<div class="approval-grid">
			<section class="panel approval-controls">
				<div class="panel-heading"><span class="eyebrow">PROPOSED HUMAN APPROVAL MODEL</span><h2>Dual-authorisation review</h2><p>Try a simulated response gate requiring two separate authorised reviewers.</p></div>
				<div class="request-card"><span class="eyebrow">SAMPLE RESPONSE PROPOSAL</span><code>{proposal.id}</code><strong>Revoke a sample identity session</strong><small>{proposal.tenantId} · {proposal.incidentId} · Proposer: {proposal.proposedBy}</small></div>
				<label class="check"><input type="checkbox" bind:checked={socApproved}/><span><strong>SOC lead approval</strong><small>Recorded by fictitious lead-1</small></span></label>
				<label class="check"><input type="checkbox" bind:checked={customerApproved}/><span><strong>Customer administrator approval</strong><small>Recorded by fictitious customer-1</small></span></label>
				<label class="check reject"><input type="checkbox" bind:checked={rejected}/><span><strong>Customer administrator rejects the action</strong><small>Rejection vetoes the proposal in this model</small></span></label>
				<button type="button" class="reset" on:click={() => {socApproved=false;customerApproved=false;rejected=false;}}>Reset example approvals ↺</button>
			</section>
			<section class="panel approval-outcome">
				<div class="panel-heading"><span class="eyebrow">PREVIEW GATE STATUS</span><h2>Approval readiness</h2></div>
				<div class="decision-result" class:permitted={readiness.ready}><span>MODEL STATUS</span><h3>{readiness.ready ? 'Hypothetical criteria met' : 'Approval incomplete'}</h3><p>{readiness.reason}</p></div>
				<div class="explain"><span class="eyebrow">NEVER AN EXECUTION APPROVAL</span><p>Even when the example policy is satisfied, RH Sentry has no executor and no customer authority to perform the action. The current response-centre demo remains entirely disconnected.</p></div>
				<div class="guarantees">
					<div><span>01</span><strong>Independent reviewers</strong><p>SOC lead and customer administrator identities must differ from the proposer and from each other.</p></div>
					<div><span>02</span><strong>Expiry and scope</strong><p>Real approvals must bind to a specific tenant, target, proposed action and expiry.</p></div>
					<div><span>03</span><strong>Backend checks and audit</strong><p>A production service must re-evaluate identities, approvals and authorisation transactionally and produce tamper-resistant records.</p></div>
				</div>
			</section>
		</div>
	{:else}
		<div class="contract-grid">
			<section class="panel contract-card"><span class="eyebrow">CONTRACT 01 / IDENTITY</span><h2>Identity and membership</h2><p>Authenticated principal, active account status, explicit tenant memberships and narrowly defined roles.</p><div class="schema">IdentityContext
  actorId
  active
  platformRole
  memberships[]
    tenantId
    role
    active</div><small>Client cannot assert or modify its own trusted identity context.</small></section>
			<section class="panel contract-card"><span class="eyebrow">CONTRACT 02 / INCIDENTS</span><h2>Tenant-bound records</h2><p>Every incident includes its owning tenant, evidence references, status and assigned analyst.</p><div class="schema">SentryIncidentRecord
  id
  tenantId
  severity / status
  createdAt / lastActivityAt
  evidenceRefs[]
  assignedActorId</div><small>Server must filter tenant ownership before pagination, search or aggregation.</small></section>
			<section class="panel contract-card"><span class="eyebrow">CONTRACT 03 / RESPONSE</span><h2>Scoped response proposals</h2><p>Exact incident, action, target and lifecycle dates, followed by independently verified decisions.</p><div class="schema">SentryResponseProposal
  id / tenantId
  incidentId
  proposedBy
  actionType
  targetResourceId
  createdAt / expiresAt</div><small>Approval is not execution. Executor must be separately isolated and authorised.</small></section>
			<section class="panel contract-card"><span class="eyebrow">CONTRACT 04 / AUDIT</span><h2>Verifiable event trail</h2><p>Decision outcomes, actor, resource, tenant and correlation IDs belong in a secured append-only event trail.</p><div class="schema">SentryAuditEvent
  eventId
  tenantId / actorId
  permission / resourceId
  outcome / reason
  correlationId
  occurredAt</div><small>No persistent or tamper-resistant auditing is currently implemented.</small></section>
		</div>
		<section class="panel architecture-next"><span class="eyebrow">NEXT IMPLEMENTATION BOUNDARY</span><h2>What must exist before connecting real customer data</h2><p>Build an authenticated server-side API, enforce ownership at the query boundary, issue short-lived sessions, protect state-changing requests, implement least-privilege access and persistent audit, and independently test cross-tenant leakage. Only then connect Wazuh telemetry and AI services.</p></section>
	{/if}
	<footer class="footer">RH SENTRY / SaaS SECURITY ARCHITECTURE <span>NON-OPERATIONAL POLICY PROTOTYPE · NO REAL ACCESS CONTROL</span></footer>
</div>

<style>
	.security-architecture { color:#e8eef7; }
	.warning { display:flex;align-items:center;gap:17px;background:linear-gradient(120deg,#2b222a,#151f2d);border:1px solid #70504d;border-radius:10px;padding:19px 21px;margin-bottom:18px; }
	.warn-symbol {font-size:27px;color:#e9b38a;border:1px solid #96644d;border-radius:9px;width:45px;height:45px;display:grid;place-items:center;flex-shrink:0}
	.warning strong {font-size:14px}
	.warning p {color:#b5b7c3;font-size:12px;line-height:1.7;margin:6px 0 0}
	.offline {color:#f2c399;border:1px solid #845d43;border-radius:5px;font-size:10px;letter-spacing:.05em;font-weight:800;padding:10px;white-space:nowrap;margin-left:auto}
	.stats {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:21px}
	.stats>div {background:#121b27;border:1px solid #2c394a;padding:18px;border-radius:9px;display:flex;flex-direction:column;gap:9px}
	.stats span {color:#90a1b6;font-size:10px;font-weight:800;letter-spacing:.07em}
	.stats strong {font-size:33px}
	.stats small {color:#8797aa;font-size:11px}
	.tabs {border-bottom:1px solid #2c3849;display:flex;flex-wrap:wrap;gap:26px;margin-bottom:18px}
	.tabs button {border:0;border-bottom:2px solid transparent;background:transparent;color:#94a6bb;font-size:12px;font-weight:750;padding:13px 2px 15px;cursor:pointer}
	.tabs button.active {border-color:#ed536a;color:#fce2e6}
	.access-grid,.approval-grid {display:grid;grid-template-columns:minmax(300px,.85fr) minmax(400px,1.55fr);gap:16px;align-items:start}
	.panel {background:#111a26;border:1px solid #2d3a4b;border-radius:10px;min-width:0;overflow:hidden}
	.controls,.approval-controls,.decision,.approval-outcome {padding-bottom:24px}
	.panel-heading {padding:24px 23px 17px}
	.eyebrow {font-size:10px;font-weight:800;letter-spacing:.12em;color:#e36c7b}
	.panel h2 {font-size:19px;margin:10px 0;font-weight:760}
	.panel-heading p {color:#a0b1c3;font-size:12px;line-height:1.7;margin:5px 0 0}
	.control {padding:0 22px 18px;display:flex;flex-direction:column;gap:8px}
	.control label {color:#a0b1c3;font-size:10px;font-weight:800;letter-spacing:.08em}
	.control select {width:100%;font-size:12px;padding:12px;color:#e8eef7;background:#0b131e;border:1px solid #38485b;border-radius:7px}
	.control select option {background:#101825}
	.request-card {background:#0b131e;border:1px solid #303d4e;border-radius:8px;padding:18px;margin:3px 22px;display:flex;flex-direction:column;gap:10px}
	.request-card code {font-size:12px;color:#c0d0e1;overflow-wrap:anywhere}
	.request-card strong {font-size:13px}
	.request-card small {font-size:11px;color:#899bae}
	.decision-result {margin:0 22px;padding:24px;background:#34282b;border:1px solid #85534f;border-radius:9px}
	.decision-result.permitted {background:#1c322e;border-color:#4f8a72}
	.decision-result span {font-size:10px;letter-spacing:.1em;color:#f6c49b;font-weight:800}
	.decision-result.permitted span {color:#98e5c0}
	.decision-result h3 {font-size:24px;margin:13px 0}
	.decision-result p {color:#c9c1c3;font-size:12px;line-height:1.75;margin:0}
	.explain {padding:20px 22px;border-bottom:1px solid #2c3949}
	.explain p {color:#9dafc0;font-size:12px;line-height:1.75}
	.guarantees {padding:18px 22px 2px;display:flex;flex-direction:column;gap:16px}
	.guarantees>div {display:grid;grid-template-columns:30px 1fr;gap:4px 10px}
	.guarantees>div>span {grid-row:span 2;border:1px solid #764153;color:#ed93a1;border-radius:6px;padding:7px;text-align:center;height:30px;font-size:10px;font-weight:750}
	.guarantees strong {font-size:12px}
	.guarantees p {font-size:11px;color:#91a4b8;line-height:1.7;margin:4px 0}
	.matrix {margin-top:16px}
	.table-scroll {overflow-x:auto;padding:0 22px 21px}
	.matrix table {border-collapse:collapse;width:100%;min-width:640px;font-size:12px}
	.matrix th {text-transform:capitalize;text-align:center;color:#9eafc2;font-size:11px;padding:14px;border-bottom:1px solid #3a4656}
	.matrix th:first-child,.matrix td:first-child {text-align:left}
	.matrix td {padding:13px;text-align:center;border-bottom:1px solid #283746;color:#91a0b3}
	.matrix code {color:#cad6e5;font-size:11px}
	.matrix .yes {color:#9ee1bb;font-weight:900}
	.check {display:flex;gap:13px;align-items:flex-start;border:1px solid #354256;border-radius:8px;background:#0c1520;padding:16px;margin:0 22px 11px;cursor:pointer}
	.check input {accent-color:#e75b71;margin-top:4px}
	.check strong,.check small {display:block}
	.check strong {font-size:13px}
	.check small {color:#91a5b9;font-size:11px;margin-top:7px}
	.check.reject {border-color:#604656}
	.reset {background:#302430;border:1px solid #765063;border-radius:7px;padding:11px 13px;margin:7px 22px;color:#f2bbc4;font-weight:700;font-size:11px;cursor:pointer}
	.contract-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
	.contract-card {padding:23px}
	.contract-card p {color:#a0b2c4;font-size:12px;line-height:1.7}
	.contract-card small {color:#e1b1aa;font-size:11px;line-height:1.6;display:block;margin-top:16px}
	.schema {white-space:pre-wrap;font:12px/1.8 Consolas, 'Courier New', monospace;color:#b6d2ea;background:#0a1320;border:1px solid #304256;border-radius:8px;padding:18px;margin:20px 0 0}
	.architecture-next {padding:23px;margin-top:15px}
	.architecture-next p {font-size:12px;line-height:1.9;color:#afbdcb}
	.footer {display:flex;justify-content:space-between;gap:12px;border-top:1px solid #293647;padding-top:19px;margin-top:28px;font-size:10px;font-weight:750;color:#718298;letter-spacing:.09em}
	@media(max-width:1150px){.access-grid,.approval-grid {grid-template-columns:1fr}}
	@media(max-width:750px){.stats,.contract-grid {grid-template-columns:repeat(2,minmax(0,1fr))}.warning {flex-wrap:wrap}.offline {margin-left:0}.footer {flex-direction:column}}
	@media(max-width:550px){.stats,.contract-grid {grid-template-columns:1fr}}
</style>
