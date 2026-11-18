/**
 * RH Sentry's canonical, deterministic product-navigation knowledge base.
 *
 * Future AI Analyst models must retrieve destinations and instructions from
 * this reviewed catalogue, never invent URLs/buttons or claim unavailable
 * features are operational. This file is intentionally independent of an LLM.
 */
export type SentryView =
	| 'Overview' | 'Customers' | 'Incidents' | 'AI Analyst'
	| 'Response Centre' | 'Detection Engineering' | 'Event Pipeline'
	| 'Security Architecture' | 'API Lab' | 'Assets' | 'Reports';

export type GuideEntry = {
	view: SentryView;
	title: string;
	category: 'daily' | 'advanced';
	description: string;
	terms: readonly string[];
	steps: readonly string[];
	requiresAnalyst: boolean;
	next: SentryView | null;
	nextLabel: string;
};

export const GUIDE: readonly GuideEntry[] = [
	{
		view: 'Overview', title: 'Command Centre', category: 'daily',
		description: 'Check customer investigations, priorities and monitoring coverage.',
		terms: ['dashboard', 'home', 'summary', 'overview', 'status', 'open investigations', 'start', 'monitoring'],
		steps: ['Open Command Centre', 'Use Local API / SQLite for persisted fictional records', 'Select your authorised customer', 'Open the investigation that needs attention'],
		requiresAnalyst: false, next: 'Incidents', nextLabel: 'Review incidents',
	},
	{
		view: 'Incidents', title: 'Incidents', category: 'daily',
		description: 'Work through each fictional case: understand, collect evidence, decide, then plan a response.',
		terms: ['case', 'cases', 'alert queue', 'triage', 'evidence', 'assign analyst', 'incident history', 'investigation next step', 'case workflow'],
		steps: ['Open Incidents', 'Choose Local API / SQLite and an authorised customer', 'Select a case from the prioritised queue', 'Follow Understand → Evidence → Decide → Respond', 'Use the highlighted Recommended next step to focus on what needs attention'],
		requiresAnalyst: false, next: 'Response Centre', nextLabel: 'Plan a response',
	},
	{
		view: 'Response Centre', title: 'Response Centre', category: 'daily',
		description: 'Propose actions, request lead approval and record dry-run receipts.',
		terms: ['respond', 'approval', 'approve', 'reject', 'escalate', 'playbook', 'response action', 'dry run', 'revoke session', 'isolate device'],
		steps: ['Open Response Centre', 'Select Local API / SQLite and your customer', 'Select a pending proposal or create one from an incident', 'An independent SOC lead decides', 'Record an approved dry-run receipt — no real action is executed'],
		requiresAnalyst: true, next: 'Reports', nextLabel: 'Review security reports',
	},
	{
		view: 'Assets', title: 'Assets', category: 'daily',
		description: 'Register fictional assets and link them to existing investigations.',
		terms: ['add asset', 'new asset', 'register asset', 'device', 'server', 'endpoint', 'inventory', 'owner', 'asset status'],
		steps: ['Open Assets', 'Select Local API / SQLite', 'Sign in as a SOC analyst via API Lab if editing is disabled', 'Use + Register Asset at the top-right', 'Save and optionally link an incident'],
		requiresAnalyst: false, next: 'Incidents', nextLabel: 'Open linked investigations',
	},
	{
		view: 'Reports', title: 'Reports', category: 'daily',
		description: 'Review the fictional security briefing and reporting concepts.',
		terms: ['briefing', 'report', 'executive report', 'monthly summary', 'customer report'],
		steps: ['Open Reports', 'Review the clearly marked demonstration content', 'Persistent customer-specific report generation is not connected yet'],
		requiresAnalyst: false, next: 'Overview', nextLabel: 'Return to Command Centre',
	},
	{
		view: 'AI Analyst', title: 'AI Analyst', category: 'advanced',
		description: 'Inspect the evidence-first analyst workspace. A real AI model is not connected yet.',
		terms: ['ai', 'investigate', 'analyst', 'findings', 'reasoning', 'intelligence', 'how do i', 'ask ai'],
		steps: ['Open AI Analyst', 'Choose Local API / SQLite for persisted case records', 'Select a customer and case', 'Review evidence; the current demo does not run model inference'],
		requiresAnalyst: false, next: 'Incidents', nextLabel: 'Open incident queue',
	},
	{
		view: 'Detection Engineering', title: 'Detection Engineering', category: 'advanced',
		description: 'Tune versioned detection rules and test fictional event batches.',
		terms: ['rule', 'rules', 'correlation', 'false positive', 'threshold', 'detection', 'testing', 'sigma'],
		steps: ['Open Detection Engineering', 'Choose Local API / SQLite and sign in as a SOC analyst', 'Select a versioned rule and synthetic event batch', 'Run a manual test, then review findings'],
		requiresAnalyst: true, next: 'Event Pipeline', nextLabel: 'Generate a test batch',
	},
	{
		view: 'Event Pipeline', title: 'Event Pipeline', category: 'advanced',
		description: 'Generate predefined fictional event batches and inspect correlations.',
		terms: ['event', 'events', 'log', 'logs', 'pipeline', 'wazuh', 'synthetic', 'fixture', 'ingestion'],
		steps: ['Open Event Pipeline', 'Sign in through API Lab as a SOC analyst', 'Select an approved fictional scenario', 'Generate a test batch and examine evidence IDs'],
		requiresAnalyst: true, next: 'Detection Engineering', nextLabel: 'Test a detection rule',
	},
	{
		view: 'Customers', title: 'Customers', category: 'advanced',
		description: 'View the fictional customer portfolio and customer-context preview.',
		terms: ['tenant', 'customer', 'organisation', 'client', 'company'],
		steps: ['Open Customers', 'Review fictional organisations', 'The commercial customer portal and provisioning are not connected'],
		requiresAnalyst: false, next: 'Overview', nextLabel: 'Check customer overview',
	},
	{
		view: 'Security Architecture', title: 'Security Architecture', category: 'advanced',
		description: 'Review demonstration access-control and security architecture policies.',
		terms: ['policy', 'access', 'rbac', 'security architecture', 'tenant isolation', 'permissions'],
		steps: ['Open Security Architecture', 'Review the conceptual architecture', 'Production security administration is not yet implemented'],
		requiresAnalyst: false, next: 'API Lab', nextLabel: 'Inspect local API access',
	},
	{
		view: 'API Lab', title: 'API Lab', category: 'advanced',
		description: 'Sign in to the isolated localhost API with fictional identities.',
		terms: ['login', 'sign in', 'password', 'session', 'local api', 'sqlite', 'authentication', 'connection', 'api'],
		steps: ['Open API Lab', 'Make sure the local Python API is running on 127.0.0.1:8001', 'Sign in using a fictional account and the temporary lab password', 'Return to your intended workspace'],
		requiresAnalyst: false, next: 'Overview', nextLabel: 'Open your workspace',
	}
];

export function getGuide(view: SentryView): GuideEntry {
	const entry = GUIDE.find((record) => record.view === view);
	if (!entry) throw new Error('Unknown RH Sentry destination');
	return entry;
}

export function lookupGuide(query: string): GuideEntry[] {
	const words = query.trim().toLowerCase().split(/\s+/).filter((word) => word.length > 2);
	if (words.length === 0) return GUIDE.filter((entry) => entry.category === 'daily');
	return GUIDE.map((entry) => {
		const name = entry.title.toLowerCase();
		const searchable = [entry.title, entry.description, ...entry.terms, ...entry.steps].join(' ').toLowerCase();
		const score = words.reduce((total, word) =>
			total + (name.includes(word) ? 6 : entry.terms.some((term) => term.includes(word)) ? 4 :
				searchable.includes(word) ? 1 : 0), 0
		);
		return {entry,score};
	}).filter(({score}) => score > 0)
		.sort((a,b) => b.score - a.score)
		.map(({entry}) => entry);
}

/** Search-box keyboard action: Enter opens an existing ranked destination, never a guessed route. */
export function resolveGuideDestination(query: string, selectedIndex = 0): SentryView | null {
	if (!query.trim()) return null;
	const results = lookupGuide(query).slice(0, 6);
	if (!Number.isInteger(selectedIndex) || selectedIndex < 0 || selectedIndex >= results.length) return null;
	return results[selectedIndex]?.view ?? null;
}
