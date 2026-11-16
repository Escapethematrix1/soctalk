<script lang="ts">
	import { buildDemoAssessment } from '$lib/sentry-demo/assessment';
	import type { DemoIncident } from '$lib/sentry-demo/types';

	export let incidents: DemoIncident[];
	export let selectedId: string;

	type Panel = 'Findings' | 'Evidence' | 'Response';
	type DemoDecision = 'Reviewed — proposed' | 'Rejected — no action';
	let panel: Panel = 'Findings';
	let search = '';
	let analysed: Record<string, boolean> = {};
	let decisions: Record<string, DemoDecision> = {};
	let acknowledge = false;

	$: selected = incidents.find((incident) => incident.id === selectedId) ?? incidents[0];
	$: assessment = buildDemoAssessment(selected);
	$: shownCases = incidents.filter((incident) =>
		[incident.title, incident.asset, incident.id, incident.category]
			.join(' ')
			.toLowerCase()
			.includes(search.trim().toLowerCase())
	);
	$: isAnalysed = analysed[selectedId] ?? false;
	$: currentDecision = decisions[selectedId] ?? null;

	function chooseIncident(id: string) {
		selectedId = id;
		panel = 'Findings';
		acknowledge = false;
	}
	function runDemoAnalysis() {
		analysed = { ...analysed, [selectedId]: true };
		panel = 'Findings';
		acknowledge = false;
	}
	function recordDecision(next: DemoDecision) {
		if (!isAnalysed || !acknowledge) return;
		decisions = { ...decisions, [selectedId]: next };
		acknowledge = false;
		panel = 'Response';
	}
</script>

<div class="analyst-layout">
	<aside class="queue card" aria-label="Demo investigation queue">
		<div class="queue-top">
			<p class="kicker">OPERATIONS / CASE QUEUE</p>
			<h2>Investigations <span>{incidents.length}</span></h2>
			<p class="helper">Choose a sample case to inspect its hypothetical investigation.</p>
		</div>
		<div class="queue-search">
			<label for="sentry-analyst-search" class="sr-only">Find a sample investigation</label>
			<input id="sentry-analyst-search" type="search" placeholder="Search cases or assets..." bind:value={search} />
		</div>
		<div class="queue-list">
			{#each shownCases as incident (incident.id)}
				<button
					type="button"
					class="queue-item"
					class:chosen={incident.id === selectedId}
					aria-pressed={incident.id === selectedId}
					on:click={() => chooseIncident(incident.id)}
				>
					<div class="queue-heading">
						<span>{incident.id}</span>
						<span class:crit={incident.severity === 'Critical'} class:high={incident.severity === 'High'} class="priority">{incident.severity}</span>
					</div>
					<strong>{incident.title}</strong>
					<span class="queue-asset">{incident.asset}</span>
					<div class="queue-foot">
						<span>{incident.status}</span>
						{#if analysed[incident.id]}
							<span class="reviewed">Sample analysis ready</span>
						{/if}
					</div>
				</button>
			{:else}
				<p class="no-cases">No matching demonstration incidents.</p>
			{/each}
		</div>
	</aside>

	<section class="workbench card" aria-label="AI Analyst design prototype">
		<div class="workbench-heading">
			<div class="title-stack">
				<p class="kicker">RH SENTRY / INTELLIGENCE WORKBENCH</p>
				<div class="analyst-identity"><span class="analyst-mark" aria-hidden="true">✳</span><h2>AI Analyst <span>Workspace</span></h2></div>
				<p class="helper">Evidence first. Human decision always.</p>
			</div>
			<span class="demo-badge">PREAUTHORED DEMO · NO AI CONNECTED</span>
		</div>

		<div class="case-banner">
			<div><span class="banner-label">ACTIVE DEMONSTRATION CASE</span><h3>{selected.title}</h3><p>{selected.id} <span>·</span> {selected.asset}</p></div>
			<div class="case-meta">
				<span>{selected.severity} priority</span>
				<strong>{selected.status}</strong>
			</div>
		</div>

		<div class="investigation-progress" aria-label="Simulated investigation process">
			<div class="progress-item complete"><span class="step-circle">01</span><div><strong>Detection</strong><small>Sample event</small></div></div>
			<div class:complete={isAnalysed} class="progress-item"><span class="step-circle">02</span><div><strong>Investigation</strong><small>{isAnalysed ? 'Example prepared' : 'Not started'}</small></div></div>
			<div class:complete={Boolean(currentDecision)} class="progress-item"><span class="step-circle">03</span><div><strong>Analyst decision</strong><small>{currentDecision ? 'Demo recorded' : 'Not recorded'}</small></div></div>
		</div>

		{#if !isAnalysed}
			<div class="analysis-placeholder">
				<div class="placeholder-mark" aria-hidden="true">◎</div>
				<h3>Ready to examine the signal</h3>
				<p>Launch a sample investigation to reveal prewritten findings, supporting signals, uncertainty, timeline and a proposed next step. Nothing is analysed by an AI model yet.</p>
				<button type="button" class="action-button" on:click={runDemoAnalysis}>Run simulated investigation <span>↗</span></button>
				<div class="fine-print">This action only updates the browser interface. It does not contact servers or change endpoints.</div>
			</div>
		{:else}
			<div class="tab-row" role="tablist" aria-label="Investigation sections">
				{#each (['Findings', 'Evidence', 'Response'] as Panel[]) as name}
					<button type="button" role="tab" id={'rh-tab-' + name.toLowerCase()} aria-selected={panel === name} class:tab-active={panel === name} on:click={() => (panel = name)}>{name}</button>
				{/each}
			</div>

			{#if panel === 'Findings'}
				<div class="finding-box">
					<div class="callout-title"><span class="focus-symbol" aria-hidden="true">◈</span> INVESTIGATIVE QUESTION</div>
					<h3>{assessment.question}</h3>
					<div class="finding-grid">
						<div><span class="field-label">WORKING HYPOTHESIS</span><p>{assessment.hypothesis}</p></div>
						<div><span class="field-label">BENIGN ALTERNATIVE</span><p>{assessment.alternative}</p></div>
					</div>
				</div>
				<div class="finding-stack">
					<div><span class="field-label">WHY THIS MATTERS</span><p>{assessment.whyItMatters}</p></div>
					<div class="uncertainty"><span class="field-label">EVIDENCE GAP / UNCERTAINTY</span><p>{assessment.uncertainty}</p></div>
					<div><span class="field-label">ATT&CK CONTEXT</span><p>{assessment.attck}</p></div>
				</div>
				<div class="next-actions"><div><strong>Next: validate the evidence</strong><p>Compare these assumptions with underlying telemetry before deciding whether the activity is malicious.</p></div><button type="button" on:click={() => (panel = 'Evidence')}>Review evidence ↗</button></div>
			{:else if panel === 'Evidence'}
				<div class="evidence-heading"><div><h3>Illustrative evidence register</h3><p>References shown here are generated fixture IDs, not verified logs.</p></div><span>{assessment.evidence.length} SAMPLE SIGNALS</span></div>
				<div class="evidence-list">
					{#each assessment.evidence as evidence (evidence.id)}
						<div class="evidence-item">
							<div class="evidence-top"><code>{evidence.id}</code><span class:signal={evidence.type === 'Signal'}>{evidence.type}</span></div>
							<strong>{evidence.source}</strong><p>{evidence.detail}</p>
						</div>
					{/each}
				</div>
				<div class="verification"><span class="field-label">REQUIRED VERIFICATION</span><ol>{#each assessment.verification as step}<li>{step}</li>{/each}</ol></div>
				<div class="next-actions"><div><strong>Next: decide how to respond</strong><p>No defensive controls are executed by this prototype.</p></div><button type="button" on:click={() => (panel = 'Response')}>Review proposal ↗</button></div>
			{:else}
				<div class="response-proposal">
					<span class="field-label">RECOMMENDED ANALYST NEXT STEP · SIMULATED</span>
					<h3>{assessment.recommendedResponse}</h3>
					<p>{assessment.approvalReason}</p>
				</div>
				<div class="approval-banner"><span aria-hidden="true">⚑</span><div><strong>Approval gate — prototype only</strong><p>Recording an approval here does not trigger endpoint isolation, account changes, external webhooks or any real response action.</p></div></div>
				{#if currentDecision}
					<div class="decision-record" role="status"><strong>Current demo decision: {currentDecision}</strong><p>This entry exists only in your local browser session and is not an auditable production record.</p></div>
				{/if}
				<label class="acknowledge"><input type="checkbox" bind:checked={acknowledge} /> <span>I understand this only records a simulated decision and performs no real action.</span></label>
				<div class="decision-buttons">
					<button type="button" class="approve" disabled={!acknowledge} on:click={() => recordDecision('Reviewed — proposed')}>Record proposed approval</button>
					<button type="button" class="reject" disabled={!acknowledge} on:click={() => recordDecision('Rejected — no action')}>Record rejection</button>
				</div>
			{/if}
		{/if}
		<div class="workbench-footer"><span>RH SENTRY / DEVELOPMENT PREVIEW</span><span>NO LIVE DETECTION · NO AI INFERENCE · NO AUTOMATED RESPONSE</span></div>
	</section>

	<aside class="context card" aria-label="Demonstration incident context">
		<div class="context-heading"><p class="kicker">CONTEXT / {selected.id}</p><h2>Event timeline</h2></div>
		<div class="timeline">{#each selected.timeline as event}<div class="timeline-row">{event}</div>{/each}</div>
		<div class="context-divider"></div>
		<div class="context-heading"><p class="kicker">CASE DETAILS</p><h2>Signal profile</h2></div>
		<div class="context-data"><div><span>Severity</span><strong>{selected.severity}</strong></div><div><span>Detection source</span><strong>{selected.category}</strong></div><div><span>Current status</span><strong>{selected.status}</strong></div><div><span>Example score</span><strong>{selected.confidence}%*</strong></div></div>
		<p class="context-note">*Invented demonstration score. Not an AI-calculated probability, risk rating or operational assurance.</p>
		<div class="context-divider"></div>
		<div class="context-policy"><strong>Operational principle</strong><p>Every alert needs evidence. Every disruptive response needs explicit authority. RH Sentry will be engineered around both.</p></div>
	</aside>
</div>

<style>
	.analyst-layout { display: grid; grid-template-columns: minmax(220px,.83fr) minmax(420px,2.1fr) minmax(215px,.9fr); gap: 15px; align-items: start; }
	.card { background: #111823; border: 1px solid #26303e; border-radius: 11px; min-width: 0; overflow: hidden; }
	.kicker { font-size: 9px; letter-spacing: .16em; font-weight: 800; color: #d35b69; margin: 0 0 12px; }
	.helper { color: #8d9aad; font-size: 11px; line-height: 1.6; margin: 7px 0 0; }
	.queue-top, .context-heading { padding: 22px 20px 12px; }
	.queue h2, .context h2 { font-size: 17px; font-weight: 750; letter-spacing: -.02em; margin: 0; color: #f1f5fa; }
	.queue h2 span { color: #748498; font-size: 11px; margin-left: 7px; }
	.queue-search { padding: 11px 15px 17px; }
	.queue-search input { background: #090e17; color: #e2eaf5; border: 1px solid #313e4d; border-radius: 7px; width: 100%; padding: 12px 11px; font-size: 11px; outline: none; }
	.queue-search input:focus { border-color: #d9475d; }
	.queue-list { max-height: 660px; overflow-y: auto; }
	.queue-item { display: block; background: transparent; border: 0; border-top: 1px solid #222b39; width: 100%; color: #d6e0ed; text-align: left; padding: 16px 18px; cursor: pointer; }
	.queue-item:hover { background: #1a2432; }
	.queue-item.chosen { box-shadow: inset 3px 0 0 #e43a50; background: #241d2a; }
	.queue-heading { display: flex; justify-content: space-between; gap: 7px; margin-bottom: 9px; font-size: 10px; color: #9ba8b8; font-weight: 700; }
	.priority { color: #a5b0bd; font-weight: 700; }
	.priority.crit { color: #fb687e; }
	.priority.high { color: #f7b778; }
	.queue-item strong { display: block; font-size: 11px; line-height: 1.6; }
	.queue-asset { display: block; margin: 7px 0 10px; font-size: 10px; color: #8695a8; overflow-wrap: anywhere; }
	.queue-foot { display: flex; justify-content: space-between; gap: 8px; font-size: 9px; color: #68798e; }
	.queue-foot .reviewed { color: #91d3b6; }
	.no-cases { color: #9da9bb; padding: 15px; font-size: 12px; }
	.workbench { padding: 25px 26px 18px; }
	.workbench-heading { display: flex; align-items: start; justify-content: space-between; gap: 14px; }
	.analyst-identity { display: flex; align-items: center; gap: 11px; }
	.analyst-mark { display: grid; place-items: center; background: #3c2232; border: 1px solid #763449; border-radius: 8px; color: #f46e81; width: 38px; height: 38px; font-size: 25px; }
	.analyst-identity h2 { font-size: 20px; letter-spacing: -.025em; margin: 0; font-weight: 800; }
	.analyst-identity h2 span { font-weight: 450; color: #b5bfce; }
	.demo-badge { color: #efb4be; background: #39242e; border: 1px solid #724350; padding: 9px 10px; border-radius: 5px; font-size: 9px; font-weight: 800; letter-spacing: .05em; }
	.case-banner { display: flex; justify-content: space-between; gap: 15px; margin-top: 23px; padding: 18px; border: 1px solid #354052; background: linear-gradient(100deg,#1c2636,#151e2a); border-radius: 9px; }
	.banner-label,.field-label { font-size: 9px; letter-spacing: .12em; color: #92a0b2; font-weight: 800; }
	.case-banner h3 { font-size: 16px; font-weight: 750; margin: 8px 0; }
	.case-banner p { font-size: 10px; color: #a0acbd; margin: 0; overflow-wrap: anywhere; }
	.case-banner p span { color: #e45567; padding: 0 5px; }
	.case-meta { display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; text-align: right; font-size: 10px; color: #f7aab5; }
	.case-meta strong { color: #cfdae6; font-weight: 700; }
	.investigation-progress { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 8px; padding: 21px 0; border-bottom: 1px solid #2a3341; }
	.progress-item { display: flex; align-items: center; gap: 8px; color: #6d7d90; }
	.progress-item.complete { color: #e3ebf5; }
	.step-circle { width: 31px; height: 31px; border: 1px solid #404c5d; color: #8796a9; border-radius: 50%; display: grid; place-items: center; font-size: 10px; flex-shrink: 0; }
	.progress-item.complete .step-circle { background: #3a2632; border-color: #bc4158; color: #ffd3d9; }
	.progress-item strong { display: block; font-size: 10px; }
	.progress-item small { font-size: 9px; display: block; margin-top: 4px; color: #74859a; }
	.analysis-placeholder { padding: 44px 12px 40px; display: flex; align-items: center; flex-direction: column; text-align: center; }
	.placeholder-mark { color: #e4566a; font-size: 44px; line-height: 1; }
	.analysis-placeholder h3 { font-size: 19px; margin: 16px 0 6px; }
	.analysis-placeholder p { font-size: 12px; color: #9caabd; line-height: 1.8; max-width: 430px; }
	.action-button { border: 1px solid #e14c60; color: #fff; background: #d9344c; padding: 12px 20px; border-radius: 7px; font-size: 11px; font-weight: 800; margin-top: 13px; cursor: pointer; }
	.action-button:hover { background: #f64b63; }
	.action-button span { margin-left: 9px; }
	.fine-print { margin-top: 20px; font-size: 10px; color: #78889a; line-height: 1.6; }
	.tab-row { display: flex; gap: 25px; border-bottom: 1px solid #2d3644; }
	.tab-row button { border: 0; border-bottom: 2px solid transparent; background: transparent; padding: 19px 3px 13px; color: #8393a8; font-size: 11px; font-weight: 800; cursor: pointer; }
	.tab-row button.tab-active { color: #f7e0e4; border-color: #e5475b; }
	.finding-box { background: #0d141f; border: 1px solid #2a3442; border-radius: 8px; padding: 20px; margin-top: 21px; }
	.callout-title { color: #e36b7d; font-size: 9px; letter-spacing: .12em; font-weight: 800; display: flex; gap: 8px; }
	.focus-symbol { font-size: 14px; }
	.finding-box h3 { margin: 14px 0 21px; font-size: 18px; line-height: 1.5; letter-spacing: -.015em; font-weight: 690; }
	.finding-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 21px; border-top: 1px solid #2a3443; padding-top: 17px; }
	.finding-grid p, .finding-stack p, .response-proposal p { font-size: 11px; line-height: 1.85; color: #a5b2c2; margin: 8px 0 0; }
	.finding-stack { display: flex; flex-direction: column; gap: 15px; margin: 22px 0; }
	.finding-stack>div { border-left: 2px solid #4b5260; padding: 2px 14px; }
	.finding-stack .uncertainty { border-left-color: #d29a4c; }
	.next-actions { display: flex; gap: 12px; align-items: center; justify-content: space-between; padding: 17px 0 0; border-top: 1px solid #2d3643; }
	.next-actions strong { font-size: 12px; }
	.next-actions p { color: #8796a9; font-size: 10px; line-height: 1.6; margin: 5px 0 0; }
	.next-actions button { background: #34202c; border: 1px solid #754252; color: #f6b8c3; padding: 11px 12px; white-space: nowrap; border-radius: 6px; font-size: 10px; font-weight: 800; cursor: pointer; }
	.evidence-heading { display: flex; justify-content: space-between; gap: 10px; align-items: start; margin: 24px 0 14px; }
	.evidence-heading h3 { margin: 0 0 7px; font-size: 17px; }
	.evidence-heading p { font-size: 10px; color: #8999ac; margin: 0; }
	.evidence-heading>span { font-size: 9px; color: #c3a6af; white-space: nowrap; }
	.evidence-list { display: flex; flex-direction: column; gap: 8px; }
	.evidence-item { border: 1px solid #2b3646; border-radius: 7px; background: #0b121d; padding: 16px; }
	.evidence-top { display: flex; justify-content: space-between; gap: 7px; margin-bottom: 12px; }
	.evidence-top code { font-size: 10px; color: #f0a8b6; }
	.evidence-top span { font-size: 9px; font-weight: 700; color: #a4b2c4; }
	.evidence-top span.signal { color: #e86b7c; }
	.evidence-item strong { font-size: 12px; }
	.evidence-item p { margin: 9px 0 0; color: #9baaBD; font-size: 11px; line-height: 1.6; }
	.verification { border: 1px solid #334051; background: #1a2330; border-radius: 8px; margin: 18px 0; padding: 18px; }
	.verification ol { color: #bac6d5; margin: 12px 0 0; padding-left: 19px; display: grid; gap: 9px; font-size: 11px; line-height: 1.55; }
	.verification li::marker { color: #e36675; }
	.response-proposal { background: #161f2d; border: 1px solid #374255; border-radius: 8px; padding: 22px; margin: 25px 0; }
	.response-proposal h3 { font-size: 17px; line-height: 1.6; margin: 13px 0; font-weight: 700; }
	.approval-banner { background: #282228; border-left: 3px solid #d09a55; padding: 16px 18px; display: flex; align-items: flex-start; gap: 11px; margin-bottom: 21px; }
	.approval-banner>span { color: #f2c087; font-size: 20px; }
	.approval-banner strong { font-size: 12px; }
	.approval-banner p { font-size: 11px; line-height: 1.65; color: #c5b9ba; margin: 6px 0 0; }
	.acknowledge { display: flex; gap: 10px; align-items: start; color: #abb7c5; font-size: 11px; line-height: 1.65; cursor: pointer; }
	.acknowledge input { margin-top: 4px; accent-color: #e34c62; }
	.decision-buttons { display: flex; gap: 9px; margin-top: 15px; flex-wrap: wrap; }
	.decision-buttons button { border-radius: 6px; padding: 12px 16px; font-size: 11px; font-weight: 750; border: 1px solid; cursor: pointer; }
	.decision-buttons button:disabled { opacity: .35; cursor: not-allowed; }
	.approve { background: #254539; border-color: #3c8065 !important; color: #aeedd3; }
	.reject { background: #2e2530; border-color: #755265 !important; color: #f0b8c5; }
	.decision-record { border: 1px solid #466b60; background: #192a2b; color: #bdedda; padding: 14px; border-radius: 7px; font-size: 11px; margin: 17px 0; }
	.decision-record p { color: #96b6ac; margin: 6px 0 0; line-height: 1.6; }
	.workbench-footer { display: flex; justify-content: space-between; gap: 10px; border-top: 1px solid #293342; padding-top: 16px; margin-top: 25px; font-size: 9px; font-weight: 700; letter-spacing: .07em; color: #697b90; }
	.context { padding-bottom: 20px; }
	.context .context-heading h2 { font-size: 17px; }
	.timeline { display: flex; flex-direction: column; margin: 16px 20px 22px 27px; border-left: 1px solid #8b4154; padding-left: 19px; gap: 24px; }
	.timeline-row { position: relative; font-size: 11px; color: #a7b4c5; line-height: 1.65; overflow-wrap: anywhere; }
	.timeline-row:before { content: ''; display: block; width: 8px; height: 8px; background: #e14d60; position: absolute; left: -24px; top: 5px; border-radius: 50%; border: 2px solid #111823; }
	.context-divider { margin: 22px 20px 0; height: 1px; background: #293443; }
	.context-data { padding: 10px 20px; display: grid; gap: 14px; }
	.context-data>div { display: flex; justify-content: space-between; gap: 11px; font-size: 10px; line-height: 1.5; }
	.context-data span { color: #8291a6; }
	.context-data strong { color: #c9d6e3; font-weight: 670; text-align: right; }
	.context-note { color: #76869b; font-size: 10px; line-height: 1.7; padding: 0 20px; }
	.context-policy { margin: 22px 20px 0; padding: 17px; background: #1b232f; border-radius: 7px; }
	.context-policy strong { font-size: 11px; }
	.context-policy p { color: #92a4b6; font-size: 11px; line-height: 1.7; margin: 7px 0 0; }
	.sr-only { position: absolute; height: 1px; width: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; }
	@media (max-width: 1550px) {
		.analyst-layout { grid-template-columns: minmax(220px,.85fr) minmax(400px,1.8fr); }
		.context { grid-column: 1 / -1; }
		.context-data { grid-template-columns: 1fr 1fr; }
	}
	@media (max-width: 1050px) {
		.analyst-layout { grid-template-columns: minmax(0,1fr); }
		.context { grid-column: auto; }
	}
	@media (max-width: 650px) {
		.workbench { padding: 18px 15px; }
		.workbench-heading,.case-banner,.next-actions,.evidence-heading { flex-direction: column; }
		.case-meta { text-align: left; }
		.finding-grid { grid-template-columns: 1fr; }
		.demo-badge { display: inline-block; }
		.investigation-progress { gap: 4px; }
		.progress-item { align-items: flex-start; flex-direction: column; }
		.workbench-footer { flex-direction: column; }
		.context-data { grid-template-columns: 1fr; }
	}
</style>
