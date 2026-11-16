import type { DemoAssessment, DemoIncident } from './types';

/**
 * Deterministic, preauthored demonstration data. This is NOT AI inference.
 * It does not read telemetry, make network requests, or execute actions.
 * The real product will replace it with evidence-grounded API data.
 */
const scenarios: Record<string, Omit<DemoAssessment, 'evidence'>> = {
	'SEN-2048': {
		question: 'Was the identity actually compromised, or is this a location anomaly?',
		hypothesis: 'The two sign-ins could indicate that an unauthorised party obtained a valid session.',
		alternative: 'A VPN egress change, mobile carrier routing or imprecise IP geolocation could explain the distance.',
		attck: 'Possible T1078 — Valid Accounts (requires validation)',
		whyItMatters: 'An attacker using legitimate credentials may bypass prevention controls and blend into normal activity.',
		uncertainty: 'The sample lacks device attestation, IP reputation, full MFA outcome and session continuity data.',
		recommendedResponse: 'Ask an analyst to review the sign-in context and confirm with the account owner before considering session revocation.',
		approvalReason: 'Revoking sessions may interrupt a legitimate user and must be authorised.',
		verification: ['Correlate authentication IDs and IP sources', 'Review MFA result, device ID and session history', 'Confirm travel or VPN use with account owner']
	},
	'SEN-2047': {
		question: 'Was the PowerShell command administrative or malicious?',
		hypothesis: 'An encoded command may be masking suspicious script activity.',
		alternative: 'Approved administrative scripts and software installers frequently use encoded PowerShell.',
		attck: 'Possible T1059.001 — PowerShell (behaviour not yet attributed)',
		whyItMatters: 'Script interpreters are widely used by both administrators and attackers for system changes.',
		uncertainty: 'There is no full script body, process tree, execution result or signed-script context in the sample.',
		recommendedResponse: 'Review command content, process ancestry and the authorised change record before deciding on endpoint containment.',
		approvalReason: 'Isolating a workstation disrupts business operations and requires explicit approval.',
		verification: ['Recover the decoded script safely', 'Check parent process and execution chain', 'Compare against expected administrative activity']
	},
	'SEN-2046': {
		question: 'Did any inbound attempt bypass the edge firewall?',
		hypothesis: 'The remote source was probing for a reachable service.',
		alternative: 'It could be ordinary internet background scanning without targeted intent.',
		attck: 'Possible T1595 — Active Scanning (unconfirmed)',
		whyItMatters: 'Denied probes are useful exposure signals even if no compromise occurred.',
		uncertainty: 'Only denied events are shown; no source attribution or complete traffic capture exists.',
		recommendedResponse: 'Verify firewall policy and ensure no related accepted sessions occurred. No further containment is indicated by this sample.',
		approvalReason: 'Policy changes can interrupt legitimate access and should go through review.',
		verification: ['Compare denied events with allowed flow logs', 'Confirm service exposure and segmentation', 'Check for related authentication events']
	},
	'SEN-2045': {
		question: 'Was the mailbox rule an authorised business change?',
		hypothesis: 'An unauthorised forwarding rule might expose sensitive messages.',
		alternative: 'The owner or an approved workflow may have intentionally configured the rule.',
		attck: 'Possible T1114.003 — Email Forwarding Rule (unconfirmed)',
		whyItMatters: 'Mailbox forwarding can enable ongoing collection of business information.',
		uncertainty: 'The sample does not establish who created the rule or whether messages were forwarded.',
		recommendedResponse: 'Confirm the owner and audit trail, then seek approval before removing the rule or revoking sessions.',
		approvalReason: 'Removing a business-critical rule or revoking sessions needs authorised change control.',
		verification: ['Inspect mailbox rule and forwarding target', 'Review sign-in and mailbox audit events', 'Confirm business justification with the owner']
	},
	'SEN-2044': {
		question: 'Was this privileged-role assignment approved?',
		hypothesis: 'Unexpected elevation could create an opportunity for privilege misuse.',
		alternative: 'It may be a routine administrator change missing a linked ticket.',
		attck: 'Potential privilege escalation — insufficient evidence for a specific technique',
		whyItMatters: 'New high-privilege access increases the possible impact of an identity compromise.',
		uncertainty: 'No request ticket, role justification or correlated activity is available.',
		recommendedResponse: 'Validate assignment ownership and the change request before considering removal.',
		approvalReason: 'Removing privileges may block legitimate operational work and requires approval.',
		verification: ['Find the identity governance approval', 'Check who initiated the assignment', 'Review subsequent privileged actions']
	},
	'SEN-2043': {
		question: 'Was the missing heartbeat a connectivity issue or a security event?',
		hypothesis: 'The telemetry interruption could hide a brief visibility gap.',
		alternative: 'A restart, network delay or maintenance window is a more likely benign explanation.',
		attck: 'No supported ATT&CK technique from this evidence',
		whyItMatters: 'Missing telemetry reduces detection confidence even without an active threat.',
		uncertainty: 'The sample lacks network, host uptime and agent health diagnostics.',
		recommendedResponse: 'Check agent health and recent maintenance; do not initiate security containment for this event alone.',
		approvalReason: 'Any future disruptive action must be tied to verified risk and explicit authorisation.',
		verification: ['Inspect agent connectivity history', 'Check host uptime and updates', 'Verify events resumed after reconnection']
	}
};

const generic: Omit<DemoAssessment, 'evidence'> = {
	question: 'Does this synthetic alert represent a genuine threat or expected activity?',
	hypothesis: 'The generated signal could correspond to suspicious behaviour requiring investigation.',
	alternative: 'The same signal may result from legitimate administrative activity or lab traffic.',
	attck: 'No validated ATT&CK mapping',
	whyItMatters: 'A single detection signal does not establish a confirmed security incident.',
	uncertainty: 'This alert exists only in the browser and has no source telemetry.',
	recommendedResponse: 'Request more context and verify the source before considering any containment.',
	approvalReason: 'All response actions must be verified and separately authorised.',
	verification: ['Verify the originating event', 'Collect supporting telemetry', 'Determine whether the activity was approved']
};

export function buildDemoAssessment(incident: DemoIncident): DemoAssessment {
	const scenario = scenarios[incident.id] ?? generic;
	const evidence = incident.indicators.map((detail, index) => ({
		id: incident.id + '-E' + String(index + 1).padStart(2, '0'),
		source: index === 0 ? 'Example detection signal' : index === 1 ? 'Example enrichment' : 'Example investigation note',
		detail,
		type: (index === 0 ? 'Signal' : index === 1 ? 'Context' : 'Unknown') as const
	}));
	return { ...scenario, evidence };
}
