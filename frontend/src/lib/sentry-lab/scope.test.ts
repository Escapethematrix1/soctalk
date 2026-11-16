import { describe, expect, it } from 'vitest';
import { chooseLabCase, chooseLabTenant, hasLabEditRole, visibleLabTenants } from './scope';
import type { LabMembership, LabTenant, LabCase } from './scope';

const tenants: LabTenant[] = [
	{ id: 'alderwick', name: 'Alderwick Logistics' },
	{ id: 'summit', name: 'Summit Retail' },
	{ id: 'harbourline', name: 'Harbourline Legal' }
];
const cases: LabCase[] = [
	{ id: 'SEN-2048', tenantId: 'alderwick', title: 'Synthetic identity alert', severity: 'critical', status: 'investigating', version: 3, assignedTo: 'alderwick-lead' },
	{ id: 'SEN-2047', tenantId: 'alderwick', title: 'Synthetic endpoint alert', severity: 'high', status: 'triage', version: 1, assignedTo: null }
];

describe('local API workspace display helpers (not backend authorisation)', () => {
	it('only lists tenants disclosed for the authenticated user', () => {
		const memberships: LabMembership[] = [{ tenantId: 'alderwick', role: 'customer_viewer' }];
		expect(visibleLabTenants(tenants, memberships)).toEqual([tenants[0]]);
		expect(visibleLabTenants(tenants, [])).toEqual([]);
	});
	it('ignores platform metadata when there is no tenant membership', () => {
		expect(visibleLabTenants(tenants, [])).toHaveLength(0);
		expect(chooseLabTenant([], 'summit')).toBe('');
	});
	it('allows analyst controls only for the selected tenant and in-memory session token still gates the UI', () => {
		const memberships: LabMembership[] = [{ tenantId: 'alderwick', role: 'soc_analyst' }];
		expect(hasLabEditRole(memberships, 'alderwick')).toBe(true);
		expect(hasLabEditRole(memberships, 'summit')).toBe(false);
		expect(hasLabEditRole([{ tenantId: 'alderwick', role: 'customer_viewer' }], 'alderwick')).toBe(false);
	});
	it('reconciles stale selection after server data or tenant changes', () => {
		expect(chooseLabTenant(tenants, 'summit')).toBe('summit');
		expect(chooseLabTenant([tenants[0]], 'summit')).toBe('alderwick');
		expect(chooseLabCase(cases, 'SEN-2048')).toBe('SEN-2048');
		expect(chooseLabCase(cases, 'SEN-2045')).toBe('SEN-2048');
		expect(chooseLabCase([], 'SEN-2048')).toBe('');
	});
});
