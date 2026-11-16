/**
 * RH SENTRY DEMONSTRATION FIXTURES ONLY.
 * - No collectors, real log queries, remote requests, executable detection rules,
 *   telemetry correlation or active integrations.
 * - Deterministic synthetic events exercise illustrative rule predicates.
 * - Production efficacy and ATT&CK coverage are NOT measured here.
 */
import type { Severity } from './types';

export type DemoEventKind =
	| 'identity-login'
	| 'process-start'
	| 'firewall-deny'
	| 'mailbox-rule'
	| 'privileged-role'
	| 'agent-health';
export type DemoField = string | number | boolean;

export interface DemoEvent {
	kind: DemoEventKind;
	fields: Record<string, DemoField>;
}

export interface DemoRuleTest {
	id: string;
	name: string;
	description: string;
	expected: 'Match' | 'No match' | 'Insufficient telemetry';
	event: DemoEvent;
}

export interface DemoDetectionRule {
	id: string;
	name: string;
	family: string;
	severity: Severity;
	sourceId: string;
	technique: string;
	tactic: string;
	summary: string;
	logic: string;
	falsePositives: string[];
	linkedIncidentId: string;
	tests: DemoRuleTest[];
}

export interface DemoTelemetrySource {
	id: string;
	name: string;
	category: string;
	description: string;
	requiredEvents: string;
	gap: string;
	status: 'Not connected';
}

export type DemoDetectionOutcome = 'Match' | 'No match' | 'Insufficient telemetry';

export interface DemoDetectionResult {
	outcome: DemoDetectionOutcome;
	detail: string;
}

const event = (kind: DemoEventKind, fields: Record<string, DemoField>): DemoEvent => ({ kind, fields });
const test = (id: string, name: string, description: string, expected: DemoRuleTest['expected'], example: DemoEvent): DemoRuleTest => ({
	id, name, description, expected, event: example
});

export const demoTelemetrySources: DemoTelemetrySource[] = [
	{ id: 'identity', name: 'Cloud identity events', category: 'IDENTITY', description: 'Sign-ins, MFA outcomes and risky authentication changes', requiredEvents: 'Sign-in and authentication audit events', gap: 'No identity connector, ingestion validation or sign-in correlation.', status: 'Not connected' },
	{ id: 'endpoint', name: 'Endpoint process telemetry', category: 'ENDPOINT', description: 'Process trees, commands and endpoint health', requiredEvents: 'Process creation, ancestry and agent status', gap: 'No endpoint agent, process collector or verified host visibility.', status: 'Not connected' },
	{ id: 'network', name: 'Firewall and network flows', category: 'NETWORK', description: 'Allowed and denied flows at perimeter controls', requiredEvents: 'Firewall deny/allow events with source and destination', gap: 'No firewall integration, flow ingestion or network sensor.', status: 'Not connected' },
	{ id: 'email', name: 'Microsoft 365 audit', category: 'EMAIL', description: 'Mailbox rules, transport changes and security events', requiredEvents: 'Mailbox and unified audit events', gap: 'No Microsoft 365 tenant linked or mail auditing available.', status: 'Not connected' },
	{ id: 'privilege', name: 'Identity privilege audit', category: 'ACCESS', description: 'Elevated roles and group membership changes', requiredEvents: 'Privileged role assignments and approval records', gap: 'No role-change feed or approval register connected.', status: 'Not connected' },
	{ id: 'health', name: 'Collector health', category: 'OPERATIONS', description: 'Telemetry availability, gaps and sensor reporting', requiredEvents: 'Agent heartbeat and last-seen events', gap: 'No deployed collector or real heartbeat baselines.', status: 'Not connected' }
];

export const demoDetectionRules: DemoDetectionRule[] = [
	{
		id: 'RHS-DET-001', name: 'Impossible travel authentication', family: 'Identity & access',
		severity: 'Critical', sourceId: 'identity', technique: 'T1078 · Valid Accounts (context only)',
		tactic: 'Initial Access', summary: 'Flags geographically implausible consecutive sign-ins for investigation, not proof of compromise.',
		logic: 'Demo-only: two sign-ins less than 15 minutes apart AND more than 500 km apart.',
		falsePositives: ['VPN egress relocation', 'Mobile IP geolocation error', 'Cloud proxy location'],
		linkedIncidentId: 'SEN-2048',
		tests: [
			test('match', 'Anomalous sign-ins', 'Four minutes apart across a large simulated distance.', 'Match', event('identity-login', { minutesBetween: 4, distanceKm: 2900 })),
			test('benign', 'Ordinary login sequence', 'Two sign-ins close together from a nearby location.', 'No match', event('identity-login', { minutesBetween: 18, distanceKm: 15 })),
			test('missing', 'Missing geolocation', 'A sign-in without the geographic distance field.', 'Insufficient telemetry', event('identity-login', { minutesBetween: 4 }))
		]
	},
	{
		id: 'RHS-DET-002', name: 'Encoded PowerShell from an unusual parent', family: 'Endpoint activity',
		severity: 'High', sourceId: 'endpoint', technique: 'T1059.001 · PowerShell', tactic: 'Execution',
		summary: 'Looks for encoded PowerShell with a suspicious parent process.',
		logic: 'Demo-only: encoded command is true AND parent process trusted is false.',
		falsePositives: ['Approved endpoint management tasks', 'Software deployment tools'],
		linkedIncidentId: 'SEN-2047',
		tests: [
			test('match', 'Suspicious command ancestry', 'Encoded invocation from an untrusted example process.', 'Match', event('process-start', { encodedCommand: true, parentTrusted: false })),
			test('benign', 'Approved maintenance command', 'Same encoding with a trusted parent in the sample.', 'No match', event('process-start', { encodedCommand: true, parentTrusted: true })),
			test('missing', 'Incomplete process tree', 'Parent process trust has not been established.', 'Insufficient telemetry', event('process-start', { encodedCommand: true }))
		]
	},
	{
		id: 'RHS-DET-003', name: 'Repeated denied inbound connections', family: 'Network defence',
		severity: 'Medium', sourceId: 'network', technique: 'T1595 · Active Scanning (possible)', tactic: 'Reconnaissance',
		summary: 'Highlights bursts of denied connections without claiming a successful intrusion.',
		logic: 'Demo-only: at least 30 denied connections AND firewall action is blocked.',
		falsePositives: ['Routine internet scanning', 'Network tests by administrators'],
		linkedIncidentId: 'SEN-2046',
		tests: [
			test('match', 'Denied inbound burst', 'A synthetic firewall recorded 38 blocked attempts.', 'Match', event('firewall-deny', { deniedCount: 38, blocked: true })),
			test('benign', 'Low-rate rejected traffic', 'Only two connections were denied.', 'No match', event('firewall-deny', { deniedCount: 2, blocked: true })),
			test('missing', 'Missing firewall decision', 'No allow/deny field was provided.', 'Insufficient telemetry', event('firewall-deny', { deniedCount: 38 }))
		]
	},
	{
		id: 'RHS-DET-004', name: 'External mailbox forwarding rule', family: 'Email security',
		severity: 'High', sourceId: 'email', technique: 'T1114.003 · Email Forwarding Rule', tactic: 'Collection',
		summary: 'Surfaces potentially sensitive forwarding changes pending owner validation.',
		logic: 'Demo-only: new mailbox rule forwards to an external address.',
		falsePositives: ['Approved external mail routing', 'Legitimate forwarding workflows'],
		linkedIncidentId: 'SEN-2045',
		tests: [
			test('match', 'External forward created', 'A sample mailbox rule points to an external recipient.', 'Match', event('mailbox-rule', { externalForwarding: true, ruleCreated: true })),
			test('benign', 'Internal mail rule', 'A new rule forwards internally only.', 'No match', event('mailbox-rule', { externalForwarding: false, ruleCreated: true })),
			test('missing', 'Unknown forwarding destination', 'No recipient classification is present.', 'Insufficient telemetry', event('mailbox-rule', { ruleCreated: true }))
		]
	},
	{
		id: 'RHS-DET-005', name: 'Unapproved privileged role change', family: 'Identity & access',
		severity: 'Medium', sourceId: 'privilege', technique: 'Role change · Mapping not verified', tactic: 'Privilege Escalation',
		summary: 'Highlights role elevation that lacks a linked approval record.',
		logic: 'Demo-only: privilege granted AND approval recorded is false.',
		falsePositives: ['Emergency authorised maintenance', 'Change-ticket synchronisation delays'],
		linkedIncidentId: 'SEN-2044',
		tests: [
			test('match', 'Missing change approval', 'A sample high-privilege grant lacks approval.', 'Match', event('privileged-role', { elevatedAccess: true, approvalRecorded: false })),
			test('benign', 'Approved role change', 'The same change has a recorded approval.', 'No match', event('privileged-role', { elevatedAccess: true, approvalRecorded: true })),
			test('missing', 'Unresolved approval state', 'The approval field is missing.', 'Insufficient telemetry', event('privileged-role', { elevatedAccess: true }))
		]
	},
	{
		id: 'RHS-DET-006', name: 'Delayed endpoint heartbeat', family: 'Agent health',
		severity: 'Low', sourceId: 'health', technique: 'No ATT&CK mapping', tactic: 'Telemetry Quality',
		summary: 'Tracks monitoring visibility gaps that may not represent attacker activity.',
		logic: 'Demo-only: sample agent heartbeat delay is 7 minutes or more.',
		falsePositives: ['Scheduled system restart', 'Connectivity interruption'],
		linkedIncidentId: 'SEN-2043',
		tests: [
			test('match', 'Missing heartbeats', 'The sample agent did not report for 9 minutes.', 'Match', event('agent-health', { delayMinutes: 9 })),
			test('benign', 'Normal heartbeat', 'The sample agent checked in two minutes ago.', 'No match', event('agent-health', { delayMinutes: 2 })),
			test('missing', 'No last-seen timestamp', 'Heartbeat delay is unknown.', 'Insufficient telemetry', event('agent-health', {}))
		]
	}
];

/** Deterministic example predicate, not an authorised operational detection implementation. */
export function evaluateDemoDetection(ruleId: string, sample: DemoEvent): DemoDetectionResult {
	const ruleIndex = demoDetectionRules.findIndex((r) => r.id === ruleId);
	if (ruleIndex === -1) {
		return { outcome: 'Insufficient telemetry', detail: 'No matching illustrative rule definition.' };
	}
	const expectedKind: DemoEventKind[] = [
		'identity-login', 'process-start', 'firewall-deny',
		'mailbox-rule', 'privileged-role', 'agent-health'
	];
	if (sample.kind !== expectedKind[ruleIndex]) {
		return { outcome: 'Insufficient telemetry', detail: 'Synthetic event type is incompatible with this example rule.' };
	}
	const requiredFields: string[][] = [
		['minutesBetween', 'distanceKm'],
		['encodedCommand', 'parentTrusted'],
		['deniedCount', 'blocked'],
		['externalForwarding', 'ruleCreated'],
		['elevatedAccess', 'approvalRecorded'],
		['delayMinutes']
	];
	const requiredTypes: ('number' | 'boolean')[][] = [
		['number', 'number'],
		['boolean', 'boolean'],
		['number', 'boolean'],
		['boolean', 'boolean'],
		['boolean', 'boolean'],
		['number']
	];
	if (requiredFields[ruleIndex].some((key, position) => typeof sample.fields[key] !== requiredTypes[ruleIndex][position])) {
		return { outcome: 'Insufficient telemetry', detail: 'A required field is missing or has an invalid type in the synthetic event.' };
	}
	const f = sample.fields;
	let matched = false;
	switch (ruleId) {
		case 'RHS-DET-001':
			matched = (f.minutesBetween as number) < 15 && (f.distanceKm as number) > 500;
			break;
		case 'RHS-DET-002':
			matched = f.encodedCommand === true && f.parentTrusted === false;
			break;
		case 'RHS-DET-003':
			matched = (f.deniedCount as number) >= 30 && f.blocked === true;
			break;
		case 'RHS-DET-004':
			matched = f.externalForwarding === true && f.ruleCreated === true;
			break;
		case 'RHS-DET-005':
			matched = f.elevatedAccess === true && f.approvalRecorded === false;
			break;
		case 'RHS-DET-006':
			matched = (f.delayMinutes as number) >= 7;
			break;
	}
	return matched
		? { outcome: 'Match', detail: 'The illustrative predicate matched this synthetic event. It does not establish a genuine security threat.' }
		: { outcome: 'No match', detail: 'The illustrative predicate did not match this synthetic event. This does not establish that an environment is safe.' };
}

export function demoCoverageSummary() {
	return {
		sourceTypes: demoTelemetrySources.length,
		connectedSources: 0,
		liveRules: 0,
		exampleRules: demoDetectionRules.length,
		liveCoveragePercent: 0
	};
}
