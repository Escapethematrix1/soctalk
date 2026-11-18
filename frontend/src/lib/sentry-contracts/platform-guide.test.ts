import { describe, expect, it } from 'vitest';
import { GUIDE, getGuide, lookupGuide } from './platform-guide';

describe('RH Sentry navigation knowledge', () => {
	it('contains unique, complete destinations and an explicit next step', () => {
		expect(GUIDE).toHaveLength(11);
		expect(new Set(GUIDE.map((item) => item.view)).size).toBe(GUIDE.length);
		expect(GUIDE.every((item) => item.steps.length > 0)).toBe(true);
		for (const item of GUIDE) {
			if (item.next) expect(() => getGuide(item.next!)).not.toThrow();
		}
	});
	it('finds the intended asset registration path', () => {
		const answer = lookupGuide('where do I register a new asset')[0];
		expect(answer.view).toBe('Assets');
		expect(answer.steps.join(' ')).toContain('+ Register Asset');
	});
	it('finds response approvals and makes restricted access explicit', () => {
		const answer = lookupGuide('how can I approve a response')[0];
		expect(answer.view).toBe('Response Centre');
		expect(answer.requiresAnalyst).toBe(true);
		expect(answer.steps.join(' ')).toContain('independent SOC lead');
	});
	it('locates event batches and experimental detections', () => {
		expect(lookupGuide('Wazuh synthetic logs')[0].view).toBe('Event Pipeline');
		expect(lookupGuide('false positive rule testing')[0].view).toBe('Detection Engineering');
	});
	it('never invents destinations', () => {
		expect(lookupGuide('unrelated nonexistent feature xyzabcabc')).toEqual([]);
		expect(lookupGuide('').every((item) => item.category === 'daily')).toBe(true);
	});
	it('explicitly states that the AI workbench is not connected', () => {
		expect(getGuide('AI Analyst').description).toMatch(/not connected/);
	});
});