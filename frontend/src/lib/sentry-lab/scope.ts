/**
 * Types/helpers for the optional RH Sentry localhost API preview.
 * These helpers do not constitute an authorisation boundary: the Python
 * backend validates the session, tenant and permissions for every request.
 */
export interface LabMembership { tenantId: string; role: string }
export interface LabTenant { id: string; name: string }
export interface LabCase {
	id: string; tenantId: string; title: string; severity: string;
	status: string; version: number; assignedTo: string | null;
}
export interface LabIdentity {
	user: string;
	memberships: LabMembership[];
	demoOnly: true;
}

/** Only display metadata for tenants present in the server-issued membership list. */
export function visibleLabTenants(tenants: readonly LabTenant[], memberships: readonly LabMembership[]): LabTenant[] {
	const permitted = new Set(memberships.map((member) => member.tenantId));
	return tenants.filter((tenant) => permitted.has(tenant.id));
}
export function hasLabEditRole(memberships: readonly LabMembership[], tenantId: string): boolean {
	return memberships.some((member) =>
		member.tenantId === tenantId && (member.role === 'soc_analyst' || member.role === 'soc_lead')
	);
}
export function chooseLabTenant(available: readonly LabTenant[], current: string): string {
	return available.some((tenant) => tenant.id === current) ? current : (available[0]?.id ?? '');
}
export function chooseLabCase(cases: readonly LabCase[], current: string): string {
	return cases.some((item) => item.id === current) ? current : (cases[0]?.id ?? '');
}
