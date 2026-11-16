import { buildDemoAssessment } from './assessment';
import type { DemoIncident } from './types';

/**
 * Preview-only response planning. This module has no transport, execution,
 * platform permissions or access to real systems.
 */
export type DemoResponseDecision = 'Reviewed — proposed' | 'Rejected — no action';
export type DemoResponseState = 'Investigation required' | 'Awaiting review' | 'Decision recorded' | 'Already contained';

export interface DemoResponseRecord {
	incident: DemoIncident;
	state: DemoResponseState;
	decision: DemoResponseDecision | null;
	recommendation: string;
	authorityNote: string;
}

export function buildDemoResponseRecords(
	incidents: DemoIncident[],
	analysed: Readonly<Record<string, boolean>>,
	decisions: Readonly<Record<string, DemoResponseDecision>>
): DemoResponseRecord[] {
	return incidents.map((incident) => {
		const assessment = buildDemoAssessment(incident);
		const decision = decisions[incident.id] ?? null;
		const state: DemoResponseState =
			incident.status === 'Contained' && !decision
				? 'Already contained'
				: decision
					? 'Decision recorded'
					: analysed[incident.id]
						? 'Awaiting review'
						: 'Investigation required';
		return {
			incident,
			state,
			decision,
			recommendation: assessment.recommendedResponse,
			authorityNote: assessment.approvalReason
		};
	});
}

export function demoReviewCounts(records: DemoResponseRecord[]) {
	return {
		pending: records.filter((r) => r.state === 'Awaiting review').length,
		uninvestigated: records.filter((r) => r.state === 'Investigation required').length,
		recorded: records.filter((r) => r.state === 'Decision recorded').length,
		executed: 0 // No execution is ever possible from this demo.
	};
}
