import { describe, expect, it } from 'vitest';
import { buildDemoResponseRecords, demoReviewCounts } from './response';
import type { DemoIncident } from './types';

function fixture(id: string, status: DemoIncident['status'] = 'Investigating'): DemoIncident {
	return {
		id,
		tenantId: 'alderwick',
		title: 'Test-only event',
		category: 'Identity & access',
		asset: 'DEMO-DEVICE',
		severity: 'High',
		status,
		time: 'DEMO',
		description: 'Synthetic.',
		confidence: 50,
		indicators: ['Sample'],
		timeline: ['Sample']
	};
}

describe('preview-only response queue', () => {
	it('requires investigation before showing review-ready status', () => {
		const rows = buildDemoResponseRecords([fixture('A')], {}, {});
		expect(rows[0].state).toBe('Investigation required');
		expect(demoReviewCounts(rows)).toEqual({ pending: 0, uninvestigated: 1, recorded: 0, executed: 0 });
	});
	it('reflects recorded demo decisions without claiming execution', () => {
		const rows = buildDemoResponseRecords([fixture('A'), fixture('B')], { A: true, B: true }, { B: 'Reviewed — proposed' });
		expect(rows.map((r) => r.state)).toEqual(['Awaiting review', 'Decision recorded']);
		expect(demoReviewCounts(rows).executed).toBe(0);
		expect(rows[1].decision).toBe('Reviewed — proposed');
	});
	it('does not claim a new response is required for an already contained sample', () => {
		expect(buildDemoResponseRecords([fixture('C', 'Contained')], {}, {})[0].state).toBe('Already contained');
	});
	it('preserves a linked assessment and its authorization warning', () => {
		const row = buildDemoResponseRecords([fixture('SEN-2048')], { 'SEN-2048': true }, {})[0];
		expect(row.recommendation).toContain('analyst');
		expect(row.authorityNote).toContain('authorised');
	});
});
