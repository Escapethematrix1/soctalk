import { describe, expect, it } from 'vitest';
import { buildDemoAssessment } from './assessment';
import type { DemoIncident } from './types';

const incident: DemoIncident = {
	id: 'SEN-2048',
	title: 'Impossible travel authentication',
	category: 'Identity & access',
	asset: 'M365 / demo@demo.invalid',
	severity: 'Critical',
	status: 'Investigating',
	time: '14:32',
	description: 'Sample.',
	confidence: 91,
	indicators: ['Two sign-ins', 'Unusual device', 'MFA challenge'],
	timeline: ['14:32 · Sign-in']
};

describe('RH Sentry simulated investigation contract', () => {
	it('does not infer conclusions without context', () => {
		const result = buildDemoAssessment(incident);
		expect(result.question).toContain('compromised');
		expect(result.uncertainty.length).toBeGreaterThan(20);
		expect(result.alternative.length).toBeGreaterThan(10);
	});
	it('uses stable, traceable demonstration evidence IDs', () => {
		const result = buildDemoAssessment(incident);
		expect(result.evidence.map((e) => e.id)).toEqual(['SEN-2048-E01', 'SEN-2048-E02', 'SEN-2048-E03']);
		expect(result.evidence[0].type).toBe('Signal');
	});
	it('falls back safely for a synthetic browser-only alert', () => {
		const result = buildDemoAssessment({ ...incident, id: 'SEN-LAB-001' });
		expect(result.uncertainty).toContain('no source telemetry');
		expect(result.attck).toContain('No validated');
	});
});
