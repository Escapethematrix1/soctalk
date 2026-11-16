import { describe, expect, it } from 'vitest';
import {
	checkScopedAccess,
	checkDemoProposalReadiness,
	filterTenantFixture
} from './policy';
import type {
	IdentityContext,
	SentryResponseProposal,
	SentryReviewDecision
} from './types';

const actor = (actorId: string, role: 'soc_analyst' | 'soc_lead' | 'customer_admin' | 'customer_viewer',
	tenantId = 'alderwick'): IdentityContext => ({
	actorId, active: true, platformRole: 'none',
	memberships: [{ tenantId, role, active: true }]
});
const analyst = actor('analyst-1', 'soc_analyst');
const lead = actor('lead-1', 'soc_lead');
const customer = actor('customer-1', 'customer_admin');
const viewer = actor('viewer-1', 'customer_viewer');

const proposal: SentryResponseProposal = {
	id: 'demo-proposal-01', tenantId: 'alderwick', incidentId: 'SEN-2048',
	proposedBy: analyst.actorId, actionType: 'revoke_sessions', targetResourceId: 'demo-account-1',
	justification: 'Synthetic review of anomalous sign-in.',
	createdAt: '2026-11-16T10:00:00.000Z', expiresAt: '2026-11-16T12:00:00.000Z'
};
const approval = (actorId: string, tenantId = 'alderwick', decision: 'approve' | 'reject' = 'approve'): SentryReviewDecision => ({
	proposalId: proposal.id, actorId, tenantId, decision,
	occurredAt: '2026-11-16T10:30:00.000Z'
});
const identities = [analyst, lead, customer, viewer];
const now = '2026-11-16T11:00:00.000Z';

describe('RH Sentry proposed tenant policy (not production enforcement)', () => {
	it('denies inactive users, null identities and absent tenant scope', () => {
		expect(checkScopedAccess(null, 'alderwick', 'incidents:read').allowed).toBe(false);
		expect(checkScopedAccess({ ...analyst, active: false }, 'alderwick', 'incidents:read').allowed).toBe(false);
		expect(checkScopedAccess(analyst, null, 'incidents:read').allowed).toBe(false);
	});
	it('denies cross-tenant access, even to an active SOC analyst', () => {
		expect(checkScopedAccess(analyst, 'summit', 'incidents:read').allowed).toBe(false);
		expect(checkScopedAccess(analyst, 'harbourline', 'rules:read').allowed).toBe(false);
	});
	it('makes customer access read-only except narrowly defined customer administration', () => {
		expect(checkScopedAccess(viewer, 'alderwick', 'incidents:read').allowed).toBe(true);
		expect(checkScopedAccess(viewer, 'alderwick', 'responses:approve').allowed).toBe(false);
		expect(checkScopedAccess(customer, 'alderwick', 'responses:approve').allowed).toBe(true);
		expect(checkScopedAccess(customer, 'alderwick', 'rules:write').allowed).toBe(false);
	});
	it('platform administrators may list metadata without automatically reading tenant incidents', () => {
		const admin: IdentityContext = { actorId: 'root-1', active: true, platformRole: 'platform_admin', memberships: [] };
		expect(checkScopedAccess(admin, null, 'tenants:list').allowed).toBe(true);
		expect(checkScopedAccess(admin, 'alderwick', 'incidents:read').allowed).toBe(false);
	});
	it('requires a valid active tenant membership for every role-scoped operation', () => {
		const inactive: IdentityContext = { ...lead, memberships: [{ tenantId: 'alderwick', role: 'soc_lead', active: false }] };
		expect(checkScopedAccess(inactive, 'alderwick', 'responses:approve').allowed).toBe(false);
		expect(checkScopedAccess(lead, 'alderwick', 'rules:write').allowed).toBe(true);
	});
	it('simulated fixture filtering does not include another tenant or unassigned records', () => {
		const records = [{ id: '1', tenantId: 'alderwick' }, { id: '2', tenantId: 'summit' }, { id: '3', tenantId: '' }];
		expect(filterTenantFixture(records, 'alderwick').map((x) => x.id)).toEqual(['1']);
	});
});

describe('RH Sentry illustrative dual-response review policy', () => {
	it('denies requests with no approvals and with only one approver', () => {
		expect(checkDemoProposalReadiness(proposal, [], identities, now).ready).toBe(false);
		expect(checkDemoProposalReadiness(proposal, [approval(lead.actorId)], identities, now).ready).toBe(false);
	});
	it('requires distinct SOC lead and customer administrator approvals', () => {
		const result = checkDemoProposalReadiness(proposal, [approval(lead.actorId), approval(customer.actorId)], identities, now);
		expect(result.ready).toBe(true);
		expect(result.socApprover).toBe(lead.actorId);
		expect(result.customerApprover).toBe(customer.actorId);
		expect(result.reason).toContain('No real action');
	});
	it('rejects a proposer self-approval and unrelated customer approvals', () => {
		expect(checkDemoProposalReadiness(proposal, [approval(analyst.actorId), approval(customer.actorId)], identities, now).ready).toBe(false);
		expect(checkDemoProposalReadiness(proposal, [approval(lead.actorId), approval('foreign-customer', 'summit')], identities, now).ready).toBe(false);
	});
	it('a rejection vetoes approval, including if the approvers both approved earlier', () => {
		const result = checkDemoProposalReadiness(proposal, [
			approval(lead.actorId), approval(customer.actorId), approval(viewer.actorId, 'alderwick', 'reject')
		], identities, now);
		expect(result.ready).toBe(false);
	});
	it('refuses expired or incoherent timestamps and unauthorised proposers', () => {
		expect(checkDemoProposalReadiness(proposal, [approval(lead.actorId), approval(customer.actorId)], identities, '2026-11-16T12:01:00Z').ready).toBe(false);
		expect(checkDemoProposalReadiness({ ...proposal, proposedBy: viewer.actorId }, [], identities, now).ready).toBe(false);
		expect(checkDemoProposalReadiness({ ...proposal, expiresAt: 'invalid' }, [], identities, now).ready).toBe(false);
	});
});
