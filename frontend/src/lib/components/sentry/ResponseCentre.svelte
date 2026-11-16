<script lang="ts">
	import { buildDemoResponseRecords, demoReviewCounts } from '$lib/sentry-demo/response';
	import type { DemoResponseDecision } from '$lib/sentry-demo/response';
	import type { DemoIncident } from '$lib/sentry-demo/types';
	import { demoCustomers } from '$lib/sentry-demo/customer';
	import { buildDemoAssessment } from '$lib/sentry-demo/assessment';

	export let incidents: DemoIncident[];
	export let analysed: Record<string, boolean>;
	export let decisions: Record<string, DemoResponseDecision>;
	export let selectedId: string;
	export let onInvestigate: (id: string) => void;

	type Screen = 'Queue' | 'Playbooks' | 'Decision log';
	const screens: Screen[] = ['Queue', 'Playbooks', 'Decision log'];
	let screen: Screen = 'Queue';
	let search = '';
	let confirmed = false;
	let statusFilter = 'All';

	$: records = buildDemoResponseRecords(incidents, analysed, decisions);
	$: counts = demoReviewCounts(records);
	$: current = records.find((record) => record.incident.id === selectedId) ?? records[0];
	$: assessment = current ? buildDemoAssessment(current.incident) : null;
	$: matching = records.filter((r) => {
		const term = search.trim().toLowerCase();
		return (
			(statusFilter === 'All' || statusFilter === r.state) &&
			(!term ||
				[
					r.incident.title, r.incident.id, r.incident.asset,
					r.incident.category,
					demoCustomers.find((c) => c.id === r.incident.tenantId)?.name ?? ''
				].join(' ').toLowerCase().includes(term))
		);
	});
	$: logEntries = records.filter((r) => r.decision !== null);
	$: allowed = current && current.state === 'Awaiting review' && confirmed;

	function selectIncident(id: string) {
		selectedId = id;
		confirmed = false;
		screen = 'Queue';
	}
	function changeScreen(next: Screen) {
		screen = next;
		confirmed = false;
	}
	function record(next: DemoResponseDecision) {
		// Preview-only state: never call a server, connector, SIEM or endpoint.
		if (!allowed || !current) return;
		decisions = { ...decisions, [current.incident.id]: next };
		confirmed = false;
	}
	function customerName(id?: string): string {
		return demoCustomers.find((customer) => customer.id === id)?.name ?? 'Unassigned sample';
	}
</script>

<div class="response-shell">
	<div class="response-banner">
		<div class="banner-icon" aria-hidden="true">◎</div>
		<div><strong>Security actions require authority.</strong><p>The RH Sentry preview demonstrates analyst recommendations and approval controls. No playbook, network command, endpoint isolation or account change can run from this screen.</p></div>
		<span>EXECUTION DISABLED</span>
	</div>

	<div class="response-stats" aria-label="Simulated response workflow counts">
		<div><span>AWAITING HUMAN REVIEW</span><strong>{counts.pending.toString().padStart(2, '0')}</strong><small>Analysed sample cases</small></div>
		<div><span>NEEDS INVESTIGATION</span><strong>{counts.uninvestigated.toString().padStart(2, '0')}</strong><small>Before a review decision</small></div>
		<div><span>DECISIONS RECORDED</span><strong>{counts.recorded.toString().padStart(2, '0')}</strong><small>Browser session only</small></div>
		<div><span>ACTIONS EXECUTED</span><strong>00</strong><small>No live controls connected</small></div>
	</div>

	<div class="response-tabs" aria-label="Response Centre sections">
		{#each screens as item}
			<button type="button" class:active={screen === item} aria-pressed={screen === item} on:click={() => changeScreen(item)}>{item}</button>
		{/each}
	</div>

	{#if screen === 'Queue'}
		<div class="response-grid">
			<section class="panel queue" aria-label="Response review queue">
				<div class="panel-head">
					<div><span class="overline">RESPONSE OPERATIONS / DEMO</span><h2>Review queue</h2></div>
					<span class="small-count">{matching.length} CASES</span>
				</div>
				<div class="queue-controls">
					<label for="response-search" class="sr-only">Search incident review queue</label>
					<input id="response-search" type="search" bind:value={search} placeholder="Search cases, assets or customers..." />
					<label for="response-filter" class="sr-only">Filter review states</label>
					<select id="response-filter" bind:value={statusFilter}>
						<option value="All">All workflow states</option>
						<option value="Investigation required">Investigation required</option>
						<option value="Awaiting review">Awaiting review</option>
						<option value="Decision recorded">Decision recorded</option>
						<option value="Already contained">Already contained</option>
					</select>
				</div>
				<div class="queue-list">
					{#each matching as r (r.incident.id)}
						<button type="button" class:chosen={current?.incident.id === r.incident.id} class="queue-row" aria-pressed={current?.incident.id === r.incident.id} on:click={() => selectIncident(r.incident.id)}>
							<div class="queue-top"><span>{r.incident.id}</span><span class:critical={r.incident.severity === 'Critical'} class:high={r.incident.severity === 'High'}>{r.incident.severity}</span></div>
							<strong>{r.incident.title}</strong>
							<small>{customerName(r.incident.tenantId)}</small>
							<div class="queue-bottom"><span>{r.state}</span><span aria-hidden="true">›</span></div>
						</button>
					{:else}
						<div class="empty">No sample cases match those filters.</div>
					{/each}
				</div>
			</section>

			<section class="panel review">
				{#if current}
					<div class="panel-head">
						<div><span class="overline">PROPOSED RESPONSE / {current.incident.id}</span><h2>Decision workspace</h2></div>
						<span class="preview-tag">SIMULATED</span>
					</div>
					<div class="case-head">
						<div><span class="field">INCIDENT</span><h3>{current.incident.title}</h3><p>{customerName(current.incident.tenantId)} · {current.incident.asset}</p></div>
						<div class="state"><small>WORKFLOW STATUS</small><strong>{current.state}</strong></div>
					</div>
					<div class="response-steps" aria-label="Demonstration workflow stages">
						<div class="step step-ready"><b>01</b><div><strong>Event detected</strong><span>Sample telemetry</span></div></div>
						<div class:step-ready={Boolean(analysed[current.incident.id])} class="step"><b>02</b><div><strong>Analysis prepared</strong><span>{analysed[current.incident.id] ? 'Preauthored evidence' : 'Not reviewed'}</span></div></div>
						<div class:step-ready={Boolean(current.decision)} class="step"><b>03</b><div><strong>Decision recorded</strong><span>{current.decision ? 'In browser only' : 'Awaiting operator'}</span></div></div>
					</div>

					<div class="proposal">
						<div class="overline">RECOMMENDED NEXT STEP · NOT AN EXECUTABLE COMMAND</div>
						<p>{current.recommendation}</p>
						<div class="proposal-reason"><span>Why approval matters</span><p>{current.authorityNote}</p></div>
					</div>

					{#if current.state === 'Investigation required'}
						<div class="action-prompt"><strong>Investigation required first</strong><p>Open the AI Analyst workspace and run the simulated analysis before a demonstration decision can be recorded.</p><button type="button" on:click={() => onInvestigate(current.incident.id)}>Open AI investigation ↗</button></div>
					{:else if current.state === 'Already contained'}
						<div class="action-prompt"><strong>Already contained in the sample timeline</strong><p>No new action is proposed for this synthetic case. The historical status is illustrative only.</p></div>
					{:else if current.state === 'Decision recorded'}
						<div class="action-prompt complete"><strong>Review decision stored in demo state</strong><p>{current.decision}. This is not a real approval, an audit record, or evidence that a defensive action occurred.</p><button type="button" on:click={() => changeScreen('Decision log')}>See demo history ↗</button></div>
					{:else}
						<div class="decision-area">
							<div class="overline">HUMAN DECISION GATE / VISUAL ONLY</div>
							<p>For a real SaaS product, an authenticated authorised user would need to approve an exactly scoped action with an auditable record. This mockup only changes its own UI.</p>
							<label class="ack"><input type="checkbox" bind:checked={confirmed} /> I understand that this records a demo decision only and executes no security action.</label>
							<div class="decision-actions">
								<button type="button" class="accept" disabled={!confirmed} on:click={() => record('Reviewed — proposed')}>Record proposed approval</button>
								<button type="button" class="deny" disabled={!confirmed} on:click={() => record('Rejected — no action')}>Record rejection</button>
							</div>
						</div>
					{/if}

					{#if assessment}
						<div class="verification"><strong>Checks before a real response</strong><ul>{#each assessment.verification as step}<li>{step}</li>{/each}</ul></div>
					{/if}
				{:else}
					<div class="empty">Choose a demonstration incident to review.</div>
				{/if}
			</section>
		</div>
	{:else if screen === 'Playbooks'}
		<div class="playbook-intro"><span class="overline">RESPONSE PLAYBOOK DESIGN</span><h2>Controlled actions, never blind automation.</h2><p>The following are conceptual playbooks. No response integrations or runtime executors have been installed.</p></div>
		<div class="playbook-grid">
			{#each [
				{ number: '01', title: 'Suspicious identity activity', type: 'IDENTITY / MICROSOFT 365', verify: 'Correlate sign-in, MFA and session history', decide: 'Request account-owner confirmation', act: 'If independently approved, revoke affected sessions' },
				{ number: '02', title: 'Endpoint malware suspicion', type: 'ENDPOINT / EDR', verify: 'Review process tree, files and corroborating telemetry', decide: 'Assess operational impact of isolation', act: 'If authorised, isolate the specific endpoint' },
				{ number: '03', title: 'Unapproved mailbox forwarding', type: 'EMAIL / CLOUD', verify: 'Inspect mailbox rule creation and audit logs', decide: 'Validate the expected business workflow', act: 'If authorised, remove the offending rule' },
				{ number: '04', title: 'Firewall anomaly', type: 'NETWORK / EDGE', verify: 'Check allowed flows and service exposure', decide: 'Determine if any change is justified', act: 'If approved, apply a narrowly scoped rule change' }
			] as flow (flow.number)}
				<article class="panel playbook">
					<div class="playbook-top"><span class="playbook-number">{flow.number}</span><span class="preview-tag">DESIGN ONLY</span></div>
					<span class="overline">{flow.type}</span><h3>{flow.title}</h3>
					<ol><li><strong>Verify</strong><span>{flow.verify}</span></li><li><strong>Decide</strong><span>{flow.decide}</span></li><li><strong>Controlled action</strong><span>{flow.act}</span></li></ol>
					<div class="playbook-foot">Requires scoped permissions, evidence and an auditable approval before implementation.</div>
				</article>
			{/each}
		</div>
	{:else}
		<section class="panel log-panel">
			<div class="panel-head"><div><span class="overline">DECISION LOG / BROWSER MEMORY ONLY</span><h2>Sample review history</h2></div><span class="preview-tag">NOT AN AUDIT TRAIL</span></div>
			<p class="log-intro">These entries are local to the current RH Sentry preview session. No identity was verified, no database was updated, and no action was executed. Refreshing the page may discard them.</p>
			{#each logEntries as entry (entry.incident.id)}
				<div class="log-entry"><span class="log-marker" aria-hidden="true">✓</span><div><strong>{entry.incident.title}</strong><p>{entry.incident.id} · {customerName(entry.incident.tenantId)} · {entry.decision}</p></div><span class="log-tag">LOCAL DEMO</span></div>
			{:else}
				<div class="empty">No demo decisions recorded. Select an investigated sample case in the Review queue to try the flow.</div>
			{/each}
		</section>
	{/if}
	<div class="response-footer">RH SENTRY / PROTOTYPE RESPONSE ORCHESTRATION <span>ZERO CONNECTED EXECUTORS · ZERO REAL ACTIONS</span></div>
</div>

<style>
	.response-shell { color: #e6ecf5; }
	.response-banner { display: flex; gap: 17px; align-items: center; border: 1px solid #72534b; background: linear-gradient(110deg,#29242b,#151d29); padding: 19px 21px; border-radius: 10px; margin-bottom: 18px; }
	.banner-icon { color: #f0bc8e; border: 1px solid #8c6750; font-size: 26px; width: 43px; height: 43px; display: grid; place-items: center; border-radius: 50%; flex-shrink: 0; }
	.response-banner strong { font-size: 14px; }
	.response-banner p { color: #abb7c5; line-height: 1.7; font-size: 12px; margin: 5px 0 0; }
	.response-banner>span { white-space: nowrap; margin-left: auto; font-size: 10px; font-weight: 800; color: #f4c995; border: 1px solid #755746; padding: 9px 10px; border-radius: 5px; }
	.response-stats { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 12px; }
	.response-stats>div { border: 1px solid #303949; background: #121a26; padding: 19px; border-radius: 9px; display: flex; flex-direction: column; gap: 10px; }
	.response-stats span { color: #95a2b5; font-size: 10px; letter-spacing: .11em; font-weight: 800; }
	.response-stats strong { font-size: 32px; line-height: 1.1; }
	.response-stats small { color: #8594a8; font-size: 11px; }
	.response-tabs { display: flex; gap: 26px; border-bottom: 1px solid #313847; margin: 25px 0 18px; }
	.response-tabs button { border: 0; border-bottom: 2px solid transparent; background: transparent; color: #98a7b7; padding: 12px 1px 14px; font-size: 12px; font-weight: 800; cursor: pointer; }
	.response-tabs button.active { border-color: #e84d63; color: #fff; }
	.response-grid { display: grid; grid-template-columns: minmax(285px,.8fr) minmax(480px,1.7fr); gap: 15px; align-items: start; }
	.panel { background: #111923; border: 1px solid #293647; border-radius: 10px; min-width: 0; overflow: hidden; }
	.panel-head { display: flex; justify-content: space-between; gap: 12px; align-items: start; padding: 23px 23px 18px; }
	.overline { color: #df6677; font-size: 10px; letter-spacing: .12em; font-weight: 800; }
	.panel-head h2 { font-size: 19px; color: #f0f5fa; font-weight: 750; margin: 9px 0 0; }
	.small-count { font-size: 10px; color: #90a0b4; }
	.queue-controls { padding: 0 17px 16px; display: flex; flex-direction: column; gap: 8px; }
	.queue-controls input,.queue-controls select { border: 1px solid #364456; padding: 11px 12px; color: #dbe3ed; background: #090f18; border-radius: 6px; font-size: 12px; width: 100%; }
	.queue-controls select option { background: #121a26; }
	.queue-list { max-height: 680px; overflow-y: auto; }
	.queue-row { display: block; border: 0; border-top: 1px solid #2b3542; background: transparent; padding: 16px 19px; color: #e6edf6; text-align: left; width: 100%; cursor: pointer; }
	.queue-row:hover { background: #202b3b; }
	.queue-row.chosen { background: #2c202d; box-shadow: inset 3px 0 #e1445b; }
	.queue-top,.queue-bottom { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
	.queue-top { font-size: 11px; color: #94a4b8; margin-bottom: 10px; }
	.queue-top span.critical { color: #f27688; }
	.queue-top span.high { color: #efb87c; }
	.queue-row strong { font-size: 13px; line-height: 1.5; display: block; }
	.queue-row small { font-size: 11px; margin-top: 5px; display: block; color: #91a1b5; }
	.queue-bottom { margin-top: 12px; font-size: 11px; color: #b1bfce; }
	.queue-bottom span:last-child { color: #e25b6b; }
	.review { padding-bottom: 23px; }
	.preview-tag { border: 1px solid #75485a; background: #36232f; color: #f4bdc8; border-radius: 5px; font-size: 10px; font-weight: 800; padding: 8px 10px; white-space: nowrap; }
	.case-head { display: flex; justify-content: space-between; gap: 18px; align-items: start; background: #182332; padding: 20px; border-top: 1px solid #303e50; }
	.case-head h3 { font-size: 18px; line-height: 1.4; margin: 8px 0; }
	.case-head p { font-size: 11px; color: #9badbd; margin: 0; overflow-wrap: anywhere; }
	.field { font-size: 10px; color: #97a9bc; letter-spacing: .09em; font-weight: 700; }
	.state { display: flex; flex-direction: column; gap: 7px; text-align: right; flex-shrink: 0; }
	.state small { color: #8e9fb4; font-size: 10px; }
	.state strong { color: #f4c0c9; font-size: 11px; }
	.response-steps { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 11px; padding: 20px 23px; border-bottom: 1px solid #2b3442; }
	.step { display: flex; align-items: center; gap: 9px; color: #7b8b9f; }
	.step b { width: 34px; height: 34px; border: 1px solid #3b495c; display: grid; place-items: center; flex-shrink: 0; border-radius: 50%; font-size: 10px; }
	.step.step-ready b { border-color: #c24458; color: #ffd9de; background: #402733; }
	.step strong { display: block; font-size: 11px; color: #d7e0eb; }
	.step span { color: #8295aa; font-size: 10px; margin-top: 4px; display: block; }
	.proposal { padding: 23px; }
	.proposal>p { font-size: 15px; font-weight: 680; line-height: 1.7; margin: 12px 0 20px; }
	.proposal-reason { background: #1b2533; border-left: 3px solid #c88b59; padding: 15px; border-radius: 4px; }
	.proposal-reason span { color: #e8bf94; font-size: 11px; font-weight: 750; }
	.proposal-reason p { color: #c2bdc3; font-size: 12px; line-height: 1.7; margin: 7px 0 0; }
	.action-prompt,.decision-area { margin: 0 23px 23px; border: 1px solid #4a4250; background: #25212d; padding: 20px; border-radius: 8px; }
	.action-prompt.complete { background: #1b2b2a; border-color: #3d695d; }
	.action-prompt strong { font-size: 14px; }
	.action-prompt p,.decision-area p { color: #b1baca; font-size: 12px; line-height: 1.7; }
	.action-prompt button { cursor: pointer; margin-top: 10px; border: 1px solid #ad5967; padding: 11px 14px; border-radius: 6px; color: #ffe5e8; background: #502b3a; font-size: 12px; font-weight: 750; }
	.decision-area .overline { color: #e2b389; }
	.ack { display: flex; gap: 10px; font-size: 12px; color: #e0d6d9; align-items: start; margin: 15px 0; cursor: pointer; line-height: 1.55; }
	.ack input { accent-color: #e84962; margin-top: 3px; }
	.decision-actions { display: flex; flex-wrap: wrap; gap: 10px; }
	.decision-actions button { border: 1px solid transparent; cursor: pointer; padding: 12px 15px; font-size: 12px; font-weight: 750; border-radius: 6px; }
	.decision-actions button:disabled { opacity: .3; cursor: not-allowed; }
	.accept { background: #264437; color: #bdedd8; border-color: #48725d !important; }
	.deny { background: #3f2733; color: #ffd5df; border-color: #795061 !important; }
	.verification { margin: 0 23px; border-top: 1px solid #303c4c; padding-top: 19px; }
	.verification>strong { font-size: 12px; }
	.verification ul { padding-left: 21px; color: #9eafc2; font-size: 12px; line-height: 1.8; }
	.verification li::marker { color: #e16b7a; }
	.playbook-intro { padding: 12px 0 24px; }
	.playbook-intro h2 { font-size: 24px; margin: 11px 0 8px; }
	.playbook-intro p,.log-intro { color: #a2b1c2; font-size: 12px; line-height: 1.8; }
	.playbook-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 15px; }
	.playbook { padding: 22px; }
	.playbook-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
	.playbook-number { color: #75869b; font-size: 24px; }
	.playbook h3 { font-size: 17px; margin: 12px 0 23px; }
	.playbook ol { list-style: none; padding: 0; counter-reset: step; display: flex; flex-direction: column; gap: 13px; }
	.playbook li { display: flex; flex-direction: column; gap: 5px; border-left: 2px solid #df586b; padding-left: 14px; }
	.playbook li strong { font-size: 12px; }
	.playbook li span { color: #93a6b9; line-height: 1.6; font-size: 12px; }
	.playbook-foot { color: #aa9aaa; border-top: 1px solid #2f3846; margin-top: 25px; padding-top: 18px; line-height: 1.65; font-size: 11px; }
	.log-panel { padding-bottom: 15px; }
	.log-intro { margin: 0 23px 15px; }
	.log-entry { display: flex; align-items: center; gap: 12px; margin: 0 23px; padding: 19px 0; border-top: 1px solid #2a3545; }
	.log-marker { width: 32px; height: 32px; display: grid; place-items: center; background: #253e36; color: #9be0bf; border-radius: 50%; }
	.log-entry strong { font-size: 12px; }
	.log-entry p { font-size: 11px; color: #8e9eb0; margin: 5px 0 0; }
	.log-tag { font-size: 10px; margin-left: auto; color: #dbb6c2; white-space: nowrap; }
	.empty { padding: 25px; color: #a0aec0; font-size: 12px; line-height: 1.7; }
	.response-footer { display: flex; gap: 10px; justify-content: space-between; color: #6d7f94; font-size: 10px; font-weight: 750; letter-spacing: .1em; margin-top: 28px; padding-top: 17px; border-top: 1px solid #273241; }
	.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; }
	@media(max-width:1130px) { .response-grid { grid-template-columns: 1fr; } .response-stats { grid-template-columns: repeat(2,minmax(0,1fr)); } }
	@media(max-width:700px) { .response-banner,.case-head,.response-footer { flex-direction: column; align-items: flex-start; } .response-banner>span { margin-left: 0; } .response-stats,.playbook-grid { grid-template-columns: 1fr; } .response-steps { gap: 5px; } .step { flex-direction: column; align-items: flex-start; } .state { text-align: left; } .response-tabs { gap: 15px; } }
</style>
