/**
 * Evidence-first guidance for an RH Sentry fictional case.
 *
 * This is advisory UI logic, not a state transition engine or AI inference.
 * The Python API remains authoritative for every case change or approval.
 */
import type { LabCase } from '$lib/sentry-lab/scope';

export type CaseStage = 'review' | 'evidence' | 'decision' | 'response';

export type CaseWorkContext = {
	tenantId: string;
	incidentId: string;
	incidentVersion: number;
	evidence: {analystNoteCount: number; verifiedTelemetryCount: number};
	assets: {
		id: string; displayName: string; assetType: string;
		criticality: string; lifecycle: string; monitoringState: 'not_connected';
	}[];
	responses: {
		pending: number; approvedDryRun: number; rejected: number;
		recordedDryRuns: number;
	};
	caseChangeCount: number;
	dataSource: 'local-sqlite-fictional';
	liveTelemetry: false;
	aiInference: false;
	responseExecution: false;
};

export type Guidance = {
	stage: CaseStage;
	label: string;
	explanation: string;
	actionLabel: string;
};

export const CASE_STAGES: {id: CaseStage; label: string; description: string}[] = [
	{id: 'review', label: 'Understand', description: 'Check case details and affected assets'},
	{id: 'evidence', label: 'Evidence', description: 'Review and record analyst observations'},
	{id: 'decision', label: 'Decide', description: 'Assign and update the case'},
	{id: 'response', label: 'Respond', description: 'Open the approval-controlled response workflow'}
];

export function nextCaseAction(
	incident: LabCase,
	context: CaseWorkContext | null,
	canEdit: boolean
): Guidance {
	if (!canEdit) {
		return {stage:'review', label:'Review incident summary',
			explanation:'You have read-only access. Analyst notes and internal response decisions are restricted.',
			actionLabel:'View case'};
	}
	if (!context) {
		return {stage:'review', label:'Verify stored case context',
			explanation:'The case details are not yet verified against the local API. Do not assume evidence or response coverage.',
			actionLabel:'Review case'};
	}
	if (incident.status === 'closed') {
		return {stage:'review', label:'Case recorded as closed',
			explanation:'Review the final case record. Closure is not proof of remediation or a verified security outcome.',
			actionLabel:'Review record'};
	}
	if (!incident.assignedTo) {
		return {stage:'decision', label:'Assign an investigation owner',
			explanation:'This fictional case has no assigned analyst. Give it an owner before progressing the investigation.',
			actionLabel:'Choose an analyst'};
	}
	if (incident.status === 'triage') {
		return {stage:'decision', label:'Confirm triage and start investigation',
			explanation:'Review the case details first. Move to Investigating only when an analyst has accepted the case.',
			actionLabel:'Update case status'};
	}
	if (context.evidence.analystNoteCount === 0) {
		return {stage:'evidence', label:'Record an evidence-based observation',
			explanation:'No analyst notes have been recorded. Synthetic case metadata is not verified telemetry; document what is known and missing.',
			actionLabel:'Review evidence'};
	}
	if (context.responses.pending > 0) {
		return {stage:'response', label:'Response proposal awaiting lead review',
			explanation:'A fictional response has been proposed. A different SOC lead must review it; no live action can occur.',
			actionLabel:'Open response queue'};
	}
	if (incident.status === 'contained') {
		return {stage:'decision', label:'Review containment before closure',
			explanation:'Only close after an analyst verifies the intended outcome and documents any outstanding uncertainty.',
			actionLabel:'Review case decision'};
	}
	if (incident.status === 'investigating' && context.responses.approvedDryRun > 0) {
		return {stage:'decision', label:'Review the approved dry-run outcome',
			explanation:'A response plan was approved for simulation. This is not evidence of a real containment action.',
			actionLabel:'Review case state'};
	}
	return {stage:'response', label:'Consider an approval-controlled response',
		explanation:'The case has an owner and analyst observations. Review whether a response proposal or further evidence is appropriate.',
		actionLabel:'Review response options'};
}

/** Only allowed single-step transitions are shown; backend always enforces them. */
export function nextCaseStatuses(status: string): string[] {
	const transitions: Record<string, string[]> = {
		triage: ['triage', 'investigating'],
		investigating: ['investigating', 'contained'],
		contained: ['contained', 'closed'],
		closed: ['closed']
	};
	return transitions[status] ?? [status];
}

/** Order open, unassigned and more severe fictional cases before resolved cases. */
export function orderCasesForTriage<T extends LabCase>(cases: readonly T[]): T[] {
	const severityRank: Record<string, number> = {critical:0,high:1,medium:2,low:3};
	return [...cases].sort((left,right) => {
		const open = (item:LabCase) => item.status === 'closed' ? 1 : 0;
		const leftRank = [open(left),left.assignedTo ? 1 : 0,
			severityRank[left.severity.toLowerCase()] ?? 4];
		const rightRank = [open(right),right.assignedTo ? 1 : 0,
			severityRank[right.severity.toLowerCase()] ?? 4];
		for(let index=0;index<leftRank.length;index++){
			if(leftRank[index] !== rightRank[index]) return leftRank[index]-rightRank[index];
		}
		return left.id.localeCompare(right.id);
	});
}
