import type {
	IdentityContext,
	MembershipRole,
	SentryPermission,
	SentryResponseProposal,
	SentryReviewDecision,
	TenantId,
	TenantMembership
} from './types';

/**
 * A proposed policy model, not a security boundary.
 * This can be exercised in the browser preview for UX discussion only.
 * Never use client-side authorisation decisions to protect customer data.
 */
export const rolePermissions: Record<MembershipRole, readonly SentryPermission[]> = {
	customer_viewer: ['incidents:read', 'assets:read', 'reports:read'],
	customer_admin: ['incidents:read', 'assets:read', 'reports:read', 'responses:approve', 'members:manage'],
	soc_analyst: ['incidents:read', 'assets:read', 'reports:read', 'rules:read', 'responses:propose'],
	soc_lead: ['incidents:read', 'assets:read', 'reports:read', 'rules:read', 'rules:write', 'responses:propose', 'responses:approve']
};

export interface PolicyDecision {
	allowed: boolean;
	reason: string;
}

export function activeMembership(identity: IdentityContext, tenantId: TenantId): TenantMembership | undefined {
	return identity.memberships.find((membership) =>
		membership.active && membership.tenantId === tenantId
	);
}

export function checkScopedAccess(
	identity: IdentityContext | null,
	tenantId: TenantId | null,
	permission: SentryPermission
): PolicyDecision {
	if (!identity?.active || !identity.actorId.trim()) {
		return { allowed: false, reason: 'Unauthenticated or inactive identity.' };
	}
	if (permission === 'tenants:list') {
		return identity.platformRole === 'platform_admin'
			? { allowed: true, reason: 'Platform metadata listing role. This does not grant access to tenant records.' }
			: { allowed: false, reason: 'Only a platform administrator can request organisation metadata.' };
	}
	// Strict fail-closed rule: never derive a tenant from a selected UI view,
	// an untrusted query parameter, or a missing/default scope.
	if (!tenantId?.trim()) return { allowed: false, reason: 'Explicit tenant context is required.' };
	const membership = activeMembership(identity, tenantId);
	if (!membership) return { allowed: false, reason: 'No active membership for the requested tenant.' };
	if (!rolePermissions[membership.role].includes(permission)) {
		return { allowed: false, reason: 'The tenant membership does not allow that operation.' };
	}
	return { allowed: true, reason: 'Active tenant membership grants the requested permission.' };
}

export interface ProposalReadiness {
	ready: boolean;
	reason: string;
	socApprover: string | null;
	customerApprover: string | null;
}

/**
 * Proposed dual-approval rules for disruptive responses.
 * These checks model policy semantics only. A real service must also enforce
 * consent, action scope, expiration, transaction locking, freshness and
 * immutable audit records, and must never trust approvals from the browser.
 */
export function checkDemoProposalReadiness(
	proposal: SentryResponseProposal,
	decisions: readonly SentryReviewDecision[],
	identities: readonly IdentityContext[],
	nowIso: string
): ProposalReadiness {
	const fail = (reason: string): ProposalReadiness =>
		({ ready: false, reason, socApprover: null, customerApprover: null });

	const now = Date.parse(nowIso);
	const created = Date.parse(proposal.createdAt);
	const expires = Date.parse(proposal.expiresAt);
	if (!Number.isFinite(now) || !Number.isFinite(created) || !Number.isFinite(expires) ||
		created > now || expires <= now || expires <= created) {
		return fail('The proposed response is expired or its timestamps are invalid.');
	}
	if (!proposal.tenantId || !proposal.targetResourceId || !proposal.incidentId || !proposal.proposedBy) {
		return fail('An explicitly scoped proposal is required.');
	}
	const proposer = identities.find((i) => i.actorId === proposal.proposedBy);
	if (!proposer || !checkScopedAccess(proposer, proposal.tenantId, 'responses:propose').allowed) {
		return fail('The original proposer is not authorised for this tenant.');
	}
	const relevant = decisions.filter((d) => d.proposalId === proposal.id && d.tenantId === proposal.tenantId);
	if (relevant.some((d) => !d.actorId || !Number.isFinite(Date.parse(d.occurredAt)) ||
		Date.parse(d.occurredAt) < created || Date.parse(d.occurredAt) > now)) {
		return fail('A decision timestamp or actor is invalid.');
	}
	const valid = relevant
		.map((d) => ({ decision: d, identity: identities.find((i) => i.actorId === d.actorId) }))
		.filter((entry) =>
			entry.identity && entry.identity.actorId !== proposal.proposedBy &&
			checkScopedAccess(entry.identity, proposal.tenantId, 'responses:approve').allowed
		);
	// Only an authorised reviewer can veto the proposal; an unrelated
	// actor's forged browser data must not count as a valid review.
	if (valid.some((entry) => entry.decision.decision === 'reject')) {
		return fail('An authorised reviewer rejected this proposed action.');
	}
	const soc = valid.find((entry) => entry.decision.decision === 'approve' && activeMembership(entry.identity!, proposal.tenantId)?.role === 'soc_lead');
	const customer = valid.find((entry) => entry.decision.decision === 'approve' && activeMembership(entry.identity!, proposal.tenantId)?.role === 'customer_admin' &&
		entry.identity!.actorId !== soc?.identity?.actorId);
	if (!soc || !customer) return fail('Distinct authorised SOC lead and customer administrator approvals are required.');
	return {
		ready: true,
		reason: 'The example dual-approval policy is satisfied. No real action can execute from this model.',
		socApprover: soc.identity!.actorId,
		customerApprover: customer.identity!.actorId
	};
}

export function filterTenantFixture<T extends { tenantId: string }>(
	records: readonly T[],
	tenantId: string
): T[] {
	// Demonstration-only filter. Never treat this as data isolation.
	return records.filter((record) => record.tenantId === tenantId);
}
