import { describe, expect, it } from 'vitest';
import { demoCoverageSummary, demoDetectionRules, demoTelemetrySources, evaluateDemoDetection } from './detection';

describe('RH Sentry detection engineering design fixtures (never live monitoring)', () => {
	it('evaluates matching, benign and missing-data scenarios for every example rule', () => {
		for (const rule of demoDetectionRules) {
			for (const test of rule.tests) {
				expect(evaluateDemoDetection(rule.id, test.event).outcome, rule.id + ' / ' + test.id).toBe(test.expected);
			}
		}
	});

	it('does not consider wrong event types or absent rules to be matches', () => {
		expect(evaluateDemoDetection('RHS-DET-001', { kind: 'process-start', fields: { minutesBetween: 1, distanceKm: 1000 } }).outcome).toBe('Insufficient telemetry');
		expect(evaluateDemoDetection('RHS-DET-NONEXISTENT', { kind: 'identity-login', fields: {} }).outcome).toBe('Insufficient telemetry');
	});

	it('does not treat missing or incorrectly typed source data as benign activity', () => {
		expect(evaluateDemoDetection('RHS-DET-002', { kind: 'process-start', fields: { encodedCommand: 'true', parentTrusted: false } }).outcome).toBe('Insufficient telemetry');
		expect(evaluateDemoDetection('RHS-DET-006', { kind: 'agent-health', fields: {} }).outcome).toBe('Insufficient telemetry');
	});

	it('maintains a clear zero-live-coverage boundary', () => {
		const summary = demoCoverageSummary();
		expect(summary.connectedSources).toBe(0);
		expect(summary.liveRules).toBe(0);
		expect(summary.liveCoveragePercent).toBe(0);
		expect(summary.exampleRules).toBe(demoDetectionRules.length);
		expect(summary.sourceTypes).toBe(demoTelemetrySources.length);
		expect(demoTelemetrySources.every((source) => source.status === 'Not connected')).toBe(true);
	});

	it('assigns unique rule IDs, valid source IDs, and preexisting synthetic incident links', () => {
		expect(new Set(demoDetectionRules.map((rule) => rule.id)).size).toBe(demoDetectionRules.length);
		const sourceIds = new Set(demoTelemetrySources.map((source) => source.id));
		for (const rule of demoDetectionRules) {
			expect(sourceIds.has(rule.sourceId), rule.id).toBe(true);
			expect(rule.linkedIncidentId).toMatch(/^SEN-20/);
		}
	});
});
