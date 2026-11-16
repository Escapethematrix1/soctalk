import { describe, expect, it } from 'vitest';
import { demoCustomers, incidentsForDemoCustomer } from './customer';
import type { DemoIncident } from './types';

const create = (id: string, tenantId?: string): DemoIncident => ({
	id, tenantId, title: 'Demo case', category: 'Sample',
	asset: 'ASSET-DEMO', severity: 'Medium', status: 'Investigating',
	time: 'DEMO', description: 'Synthetic data', confidence: 50,
	indicators: [], timeline: []
});

describe('demonstration customer data scoping (not an auth boundary)', () => {
	it('never includes another demo organisation in the chosen sample list', () => {
		const cases = [create('A', 'northbridge'), create('B', 'harbourline'), create('C', 'northbridge')];
		expect(incidentsForDemoCustomer(cases, 'northbridge').map((x) => x.id)).toEqual(['A', 'C']);
	});
	it('excludes unassigned incidents', () => {
		expect(incidentsForDemoCustomer([create('A'), create('B', 'summit')], 'summit').map((x) => x.id)).toEqual(['B']);
	});
	it('provides three unique fictional customer IDs', () => {
		expect(new Set(demoCustomers.map((x) => x.id)).size).toBe(3);
		expect(demoCustomers.every((x) => x.demoContact.endsWith('.invalid'))).toBe(true);
	});
});
