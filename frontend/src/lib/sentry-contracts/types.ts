/**
 * Proposed RH Sentry SaaS service contracts, not production interfaces.
 * Keep this general-purpose model free of secrets and proprietary algorithms.
 * Authentication, authorisation, tenant filters, persistence and auditing MUST
 * be implemented and tested on the server; these types enforce none of that.
 */
export type TenantId = string;
export type ActorId = string;
export type SentryPermission =
	| 'tenants:list'
	| 'incidents:read'
	| 'assets:read'
	| 'reports:read'
	| 'rules:read'
	| 'rules:write'
	| 'responses:propose'
	| 'responses:approve'
	| 'members:manage';

export type MembershipRole = 'customer_viewer' | 'customer_admin' | 'soc_analyst' | 'soc_lead';

export interface TenantMembership {
	tenantId: TenantId;
	role: MembershipRole;
	active: boolean;
}

export interface IdentityContext {
	actorId: ActorId;
	active: boolean;
	platformRole: 'platform_admin' | 'none';
	memberships: TenantMembership[];
}

export interface TenantResource {
	id: string;
	tenantId: TenantId;
}

export interface SentryIncidentRecord extends TenantResource {
	createdAt: string;
	lastActivityAt: string;
	summary: string;
	severity: 'critical' | 'high' | 'medium' | 'low';
	status: 'open' | 'triage' | 'investigating' | 'contained' | 'closed';
	evidenceRefs: string[];
	assignedActorId: ActorId | null;
}

export interface SentryResponseProposal extends TenantResource {
	incidentId: string;
	proposedBy: ActorId;
	actionType: 'isolate_endpoint' | 'revoke_sessions' | 'remove_mail_rule' | 'block_network';
	targetResourceId: string;
	justification: string;
	createdAt: string;
	expiresAt: string;
}

export interface SentryReviewDecision {
	proposalId: string;
	tenantId: TenantId;
	actorId: ActorId;
	decision: 'approve' | 'reject';
	occurredAt: string;
}

export interface SentryAuditEvent {
	eventId: string;
	tenantId: TenantId | null;
	actorId: ActorId;
	permission: SentryPermission;
	resourceId: string | null;
	outcome: 'allowed' | 'denied';
	reason: string;
	correlationId: string;
	occurredAt: string;
}

/** Illustrative API shapes only; no endpoints are implemented here. */
export interface TenantScopedPage<T extends TenantResource> {
	tenantId: TenantId;
	items: T[];
	nextCursor: string | null;
}

export interface SentryApiError {
	code: 'UNAUTHENTICATED' | 'FORBIDDEN' | 'NOT_FOUND' | 'INVALID_REQUEST' | 'CONFLICT';
	message: string;
	correlationId: string;
}
