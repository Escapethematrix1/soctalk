/** RH Sentry PREVIEW ONLY: do not use these fixtures as live SOC evidence. */
export type Severity = 'Critical' | 'High' | 'Medium' | 'Low';
export type IncidentStatus = 'Investigating' | 'Awaiting review' | 'Contained' | 'Escalated';

export interface DemoIncident {
	id: string;
	title: string;
	category: string;
	asset: string;
	severity: Severity;
	status: IncidentStatus;
	time: string;
	description: string;
	confidence: number;
	indicators: string[];
	timeline: string[];
}

export type EvidenceType = 'Signal' | 'Context' | 'Unknown';
export interface DemoEvidence {
	id: string;
	source: string;
	detail: string;
	type: EvidenceType;
}

export interface DemoAssessment {
	question: string;
	hypothesis: string;
	alternative: string;
	attck: string;
	whyItMatters: string;
	uncertainty: string;
	recommendedResponse: string;
	approvalReason: string;
	evidence: DemoEvidence[];
	verification: string[];
}
