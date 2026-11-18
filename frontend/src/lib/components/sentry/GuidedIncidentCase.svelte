<script lang="ts">
	import type { LabCase } from '$lib/sentry-lab/scope';
	import {
		CASE_STAGES, nextCaseAction, nextCaseStatuses
	} from '$lib/sentry-contracts/incident-workflow';
	import type { CaseStage, CaseWorkContext } from '$lib/sentry-contracts/incident-workflow';

	/** Human-led casework over the loopback fictional API, never a live SOC. */
	export let tenantId: string;
	export let incident: LabCase;
	export let csrf: string;
	export let canEdit: boolean;
	export let onSaved: () => Promise<void>;
	export let onOpenResponse: (tenantId: string, incidentId: string) => void;

	type Analyst = {username:string;role:string};
	type Note = {id:number;actor:string;kind:string;note:string;createdAt:string};
	type Change = {id:number;actor:string;action:string;detail:string;version:number;occurredAt:string};

	const API = 'http://127.0.0.1:8001';
	let current: LabCase | null = null;
	let context: CaseWorkContext | null = null;
	let analysts: Analyst[] = [];
	let notes: Note[] = [];
	let history: Change[] = [];
	let stage: CaseStage = 'review';
	let newStatus = '';
	let newAssignee = '';
	let newNote = '';
	let showAllHistory = false;
	let message = '';
	let error = '';
	let busy = false;
	let loading = false;
	let revision = 0;
	let lastFetchKey = '';
	let lastSelectedKey = '';

	$: selectedKey = tenantId + '/' + incident.id;
	$: if (selectedKey !== lastSelectedKey) {
		lastSelectedKey = selectedKey;
		stage = 'review';
		showAllHistory = false;
		newNote = '';
	}
	$: fetchKey = selectedKey + '/' + incident.version + '/' + canEdit;
	$: if (fetchKey !== lastFetchKey) {
		lastFetchKey = fetchKey;
		void refresh();
	}
	$: recommended = nextCaseAction(current ?? incident, context, canEdit);
	$: nextStatuses = nextCaseStatuses(current?.status ?? incident.status);
	$: changesPending = Boolean(current &&
		(newStatus !== current.status || (newAssignee || null) !== current.assignedTo));

	async function api<T>(route: string, options: RequestInit = {}): Promise<T> {
		const response = await fetch(API + route, {
			...options,
			credentials:'include',
			cache:'no-store',
			headers:{'Content-Type':'application/json',...(options.headers ?? {})}
		});
		if (!response.ok) {
			let reason='HTTP ' + response.status;
			try {
				const data=await response.json();
				if (typeof data.detail === 'string') reason += ': ' + data.detail;
			} catch { /* Generic status remains visible for non-JSON errors. */ }
			throw new Error(reason);
		}
		return (await response.json()) as T;
	}
	function casePath() {
		return '/api/tenants/' + encodeURIComponent(tenantId) +
			'/incidents/' + encodeURIComponent(incident.id);
	}
	async function refresh() {
		const serial = ++revision;
		const expectedTenant = tenantId;
		const expectedId = incident.id;
		current = null;
		context = null;
		notes = [];
		history = [];
		analysts = [];
		loading = true;
		error = '';
		const path = casePath();
		try {
			const [record, people, evidence, changes, contextResponse] = await Promise.all([
				api<LabCase>(path),
				canEdit ? api<{tenantId:string;items:Analyst[]}>(
					'/api/tenants/' + encodeURIComponent(expectedTenant) + '/analysts'
				) : Promise.resolve({tenantId:expectedTenant,items:[] as Analyst[]}),
				canEdit ? api<{tenantId:string;incidentId:string;items:Note[]}>(path+'/evidence')
					: Promise.resolve({tenantId:expectedTenant,incidentId:expectedId,items:[] as Note[]}),
				canEdit ? api<{tenantId:string;incidentId:string;items:Change[]}>(path+'/history')
					: Promise.resolve({tenantId:expectedTenant,incidentId:expectedId,items:[] as Change[]}),
				canEdit ? api<CaseWorkContext>(path+'/work-context')
					: Promise.resolve(null),
			]);
			if (serial !== revision || expectedTenant !== tenantId || expectedId !== incident.id) return;
			if (record.tenantId !== expectedTenant || record.id !== expectedId ||
				people.tenantId !== expectedTenant || evidence.tenantId !== expectedTenant ||
				evidence.incidentId !== expectedId || changes.tenantId !== expectedTenant ||
				changes.incidentId !== expectedId ||
				(contextResponse && (
					contextResponse.tenantId !== expectedTenant ||
					contextResponse.incidentId !== expectedId ||
					contextResponse.incidentVersion !== record.version ||
					contextResponse.dataSource !== 'local-sqlite-fictional' ||
					contextResponse.liveTelemetry !== false ||
					contextResponse.aiInference !== false ||
					contextResponse.responseExecution !== false ||
					contextResponse.assets.some((asset) => asset.monitoringState !== 'not_connected')
				))) {
				throw new Error('Unexpected customer or data provenance; case context withheld.');
			}
			current = record;
			context = contextResponse;
			analysts = people.items;
			notes = evidence.items;
			history = changes.items;
			newStatus = record.status;
			newAssignee = record.assignedTo ?? '';
		} catch (err) {
			if (serial !== revision) return;
			current = null; context = null; analysts = []; notes = []; history = [];
			error = err instanceof Error ? err.message : 'Unable to verify the selected case.';
		} finally {
			if (serial === revision) loading = false;
		}
	}
	async function updateCase() {
		if (!canEdit || !current || !changesPending || busy) return;
		busy = true;
		message = ''; error = '';
		const patch: Record<string,unknown> = {expectedVersion:current.version};
		if (newStatus !== current.status) patch.status = newStatus;
		if ((newAssignee || null) !== current.assignedTo) patch.assignedTo = newAssignee || null;
		try {
			await api(casePath(), {
				method:'PATCH',headers:{'X-CSRF-Token':csrf},body:JSON.stringify(patch),
			});
			await onSaved();
			await refresh();
			message = 'Case decision saved to the versioned, fictional SQLite record.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Case update failed.';
			if (error.includes('409')) await refresh();
		} finally {busy = false;}
	}
	async function saveNote() {
		if (!canEdit || !current || busy || newNote.trim().length < 5) return;
		busy = true;
		message = ''; error = '';
		try {
			await api(casePath() + '/evidence', {
				method:'POST',headers:{'X-CSRF-Token':csrf},
				body:JSON.stringify({expectedVersion:current.version,note:newNote.trim()}),
			});
			newNote = '';
			await onSaved();
			await refresh();
			message = 'Analyst observation saved. This is a fictional note, not verified telemetry.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not save the analyst note.';
			if (error.includes('409')) await refresh();
		} finally {busy = false;}
	}
	function openResponse() {
		if (current && canEdit && context) {
			onOpenResponse(tenantId, current.id);
		}
	}
</script>

<section class="guided-case" aria-label="Guided local incident investigation">
	{#if loading && !current}
		<div class="loading">Checking current case state, evidence and customer scope...</div>
	{:else if !current}
		<div class="loading">Unable to load the case safely. Refresh the local workspace to try again.</div>
	{:else}
		<header class="case-heading">
			<div><span class="eyebrow">FICTIONAL CASE / {current.id}</span>
				<h3>{current.title}</h3>
				<p>{current.severity} severity · {current.status} ·
					{current.assignedTo ?? 'Unassigned'} · record v{current.version}</p>
			</div>
			<span class="sample">LOCAL SQLITE / NOT LIVE</span>
		</header>

		<div class="next-step">
			<div class="next-icon" aria-hidden="true">→</div>
			<div class="next-copy">
				<span class="eyebrow">RECOMMENDED NEXT STEP</span>
				<strong>{recommended.label}</strong>
				<p>{recommended.explanation}</p>
			</div>
			<button class="primary" type="button" on:click={() => (stage = recommended.stage)}>
				{recommended.actionLabel} →
			</button>
		</div>

		<nav class="stage-tabs" aria-label="Investigation workflow stages">
			{#each CASE_STAGES as item, index (item.id)}
				<button type="button" class:active={stage === item.id}
					aria-current={stage === item.id ? 'step' : undefined}
					on:click={() => (stage = item.id)}>
					<span class="stage-number">{String(index+1).padStart(2,'0')}</span>
					{item.label}
				</button>
			{/each}
		</nav>

		<div class="stage-body">
			{#if stage === 'review'}
				<div class="stage-title"><h4>Understand the incident</h4>
					<p>Start with known case metadata and assets. No real telemetry or AI findings are connected.</p></div>
				<div class="facts">
					<div><span>CASE STATUS</span><strong>{current.status}</strong></div>
					<div><span>ASSIGNED OWNER</span><strong>{current.assignedTo ?? 'Not assigned'}</strong></div>
					<div><span>SEVERITY</span><strong>{current.severity}</strong></div>
				</div>
				{#if canEdit && context}
					<div class="section-block">
						<div class="section-title"><h5>Associated assets</h5><small>{context.assets.length} linked</small></div>
						{#each context.assets as asset (asset.id)}
							<div class="asset-row">
								<div><strong>{asset.displayName}</strong><small>{asset.id} · {asset.assetType} · {asset.criticality} criticality</small></div>
								<span>NOT MONITORED</span>
							</div>
						{:else}
							<p class="muted">No fictional assets are linked to this incident. Use Assets to add a relationship when appropriate.</p>
						{/each}
					</div>
					<div class="insight">
						<strong>What is actually supported?</strong>
						<p>{context.evidence.analystNoteCount} stored analyst observation(s);
							{context.evidence.verifiedTelemetryCount} verified telemetry records.
							Case status and severity are fictional training data, not proof of a compromise.</p>
					</div>
					<details class="history-panel">
						<summary>Recorded case changes ({context.caseChangeCount})</summary>
						<div class="history-list">
							{#each history.slice(0,showAllHistory ? undefined : 5) as change (change.id)}
								<div class="history-row"><strong>{change.action} · v{change.version}</strong><small>{change.actor} · {change.occurredAt}</small><p>{change.detail}</p></div>
							{:else}<p class="muted">No analyst changes recorded yet.</p>{/each}
						</div>
						{#if history.length > 5}
							<button type="button" class="link-button" on:click={() => (showAllHistory = !showAllHistory)}>
								{showAllHistory ? 'Show fewer' : 'Show more history'}
							</button>
						{/if}
					</details>
				{:else}
					<div class="readonly">Customer-facing view only. Internal notes, asset investigation links and response decisions are restricted to SOC analyst roles.</div>
				{/if}
			{:else if stage === 'evidence'}
				<div class="stage-title"><h4>Review evidence and record observations</h4>
					<p>Analyst notes are observations, not verified sensor data. Record missing evidence and uncertainty explicitly.</p></div>
				{#if canEdit && context}
					<div class="insight"><strong>{context.evidence.analystNoteCount} stored note(s) · 0 verified telemetry sources</strong>
						<p>The local laboratory does not pull endpoint logs or independently prove the underlying event.</p></div>
					{#each notes as note (note.id)}
						<div class="note-row"><strong>Analyst note #{note.id}</strong><small>{note.actor} · {note.createdAt}</small><p>{note.note}</p></div>
					{:else}<div class="empty-inline">No analyst observations have been recorded for this fictional case.</div>{/each}
					<form class="note-form" on:submit|preventDefault={() => void saveNote()}>
						<label for="guided-case-note">Record a new observation</label>
						<textarea id="guided-case-note" rows="4" maxlength="1000" minlength="5"
							bind:value={newNote} disabled={busy}
							placeholder="Example: Synthetic event suggests unusual behaviour, but account ownership and source log are not verified."/>
						<div class="form-footer"><small>{newNote.length}/1000 characters · plain text only</small>
							<button class="primary" type="submit" disabled={busy || newNote.trim().length < 5}>Save analyst note</button></div>
					</form>
				{:else}
					<div class="readonly">Internal analyst notes are not accessible to customer viewer accounts.</div>
				{/if}
			{:else if stage === 'decision'}
				<div class="stage-title"><h4>Record the analyst's decision</h4>
					<p>Set ownership and advance only through permitted case states. Saved changes are versioned and audited by the API.</p></div>
				{#if canEdit && context}
					<div class="decision-card">
						<form on:submit|preventDefault={() => void updateCase()}>
							<div class="form-grid">
								<label for="guided-assignee">Assigned analyst
									<select id="guided-assignee" bind:value={newAssignee} disabled={busy}>
										<option value="">Unassigned</option>
										{#each analysts as person (person.username)}
											<option value={person.username}>{person.username} · {person.role}</option>
										{/each}
									</select>
								</label>
								<label for="guided-status">Case state
									<select id="guided-status" bind:value={newStatus} disabled={busy}>
										{#each nextStatuses as value (value)}
											<option value={value}>{value}</option>
										{/each}
									</select>
								</label>
							</div>
							<p class="muted">Allowed next states: {nextStatuses.join(' → ')}. Closing a case does not automatically verify remediation.</p>
							<button type="submit" class="primary" disabled={busy || !changesPending}>Save case decision</button>
						</form>
					</div>
					<p class="muted">For a response approval, use the Response stage. A case status update does not execute a containment action.</p>
				{:else}
					<div class="readonly">Only SOC analysts and leads may change case ownership and status.</div>
				{/if}
			{:else if stage === 'response'}
				<div class="stage-title"><h4>Plan a controlled response</h4>
					<p>Review any existing proposals before initiating another. Every response is a fictional dry-run.</p></div>
				{#if canEdit && context}
					<div class="facts">
						<div><span>AWAITING APPROVAL</span><strong>{context.responses.pending}</strong></div>
						<div><span>APPROVED DRY-RUNS</span><strong>{context.responses.approvedDryRun}</strong></div>
						<div><span>RECEIPTS RECORDED</span><strong>{context.responses.recordedDryRuns}</strong></div>
					</div>
					<div class="response-cta">
						<div><strong>Response Centre</strong>
							<p>Use the approval-controlled workflow to propose a response for this exact customer and incident. A separate SOC lead must approve a dry-run.</p></div>
						<button class="primary" type="button" on:click={openResponse}>Open this case in Response Centre →</button>
					</div>
					<div class="insight"><strong>No endpoint action can be executed</strong>
						<p>Approval and dry-run receipts do not indicate successful containment or restoration. No live response connectors are attached.</p></div>
				{:else}
					<div class="readonly">Internal response approval records require SOC analyst access.</div>
				{/if}
			{/if}
		</div>
	{/if}

	{#if error}<p class="feedback error" role="alert">{error}</p>{/if}
	{#if message}<p class="feedback" role="status">{message}</p>{/if}
	<div class="disclaimer">RH SENTRY · GUIDED FICTIONAL CASEWORK · NO LIVE SIEM · NO AUTOMATED RESPONSE · NO AI MODEL</div>
</section>

<style>
	.guided-case{color:#e9f1f9}
	.case-heading{padding:21px 21px 18px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;border-bottom:1px solid #2b3a4b}
	.case-heading h3{font-size:18px;margin:8px 0;line-height:1.45}
	.case-heading p{color:#9bb0c3;font-size:11px;margin:0;line-height:1.6;text-transform:capitalize}
	.eyebrow{color:#e66c81;letter-spacing:.1em;font-size:10px;font-weight:800}
	.sample{font-size:10px;border:1px solid #79556b;color:#eab6c0;padding:8px;border-radius:5px;white-space:nowrap}
	.next-step{display:flex;align-items:center;gap:14px;padding:16px 19px;background:#1b2534;border-bottom:1px solid #35475b}
	.next-icon{width:34px;height:34px;border-radius:7px;border:1px solid #9d4d62;color:#f1a5b4;flex-shrink:0;display:grid;place-items:center;font-size:19px}
	.next-copy{min-width:0;flex:1}.next-copy strong{font-size:14px;display:block;margin:6px 0}
	.next-copy p{font-size:11px;color:#aebdd0;line-height:1.65;margin:0}
	.primary{background:#d93653;border:1px solid #e8516c;color:#fff;padding:11px 13px;border-radius:6px;font-size:11px;font-weight:750;cursor:pointer}
	.primary:disabled{opacity:.4;cursor:not-allowed}
	.stage-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-bottom:1px solid #293a4b}
	.stage-tabs button{padding:14px 8px;background:transparent;color:#a2b6ca;border:0;border-right:1px solid #293a4b;font-size:12px;font-weight:750;cursor:pointer}
	.stage-tabs button.active{color:#fff;background:#392633;box-shadow:inset 0 -3px #e24a65}
	.stage-number{color:#db8195;margin-right:8px;font-size:10px}
	.stage-body{padding:21px;min-height:250px}
	.stage-title h4{font-size:17px;margin:0 0 8px}
	.stage-title p,.muted{font-size:11px;color:#a1b5c9;line-height:1.8;margin:0 0 16px}
	.facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin:17px 0}
	.facts>div{display:flex;flex-direction:column;gap:10px;background:#0c1622;border:1px solid #2f4054;border-radius:7px;padding:13px}
	.facts span{font-size:10px;letter-spacing:.06em;color:#91a9c0;font-weight:800}
	.facts strong{font-size:13px;text-transform:capitalize;overflow-wrap:anywhere}
	.section-block{margin:18px 0 16px;border:1px solid #2c3d4f;border-radius:8px;overflow:hidden}
	.section-title{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 16px;background:#152132}
	.section-title h5{font-size:13px;margin:0}.section-title small{color:#a1b3c6;font-size:11px}
	.asset-row{padding:13px 16px;border-top:1px solid #2c3d4f;display:flex;justify-content:space-between;align-items:center;gap:15px}
	.asset-row strong{font-size:12px}.asset-row small{display:block;margin-top:7px;font-size:10px;color:#9cafc2}
	.asset-row>span{font-size:9px;white-space:nowrap;font-weight:800;color:#dcb08b}
	.insight{margin:15px 0;background:#182538;border-left:3px solid #698ba9;padding:15px}
	.insight strong{font-size:12px}.insight p{font-size:11px;line-height:1.75;color:#aebed0;margin:7px 0 0}
	.history-panel{margin:16px 0;border:1px solid #304357;border-radius:7px;padding:13px 15px}
	.history-panel summary{cursor:pointer;color:#b9cadb;font-size:12px;font-weight:750}
	.history-list{margin-top:12px}.history-row{border-top:1px solid #2e4052;padding:12px 0}
	.history-row strong{font-size:11px}.history-row small{font-size:10px;color:#92a8bc;display:block;margin:6px 0}
	.history-row p{font-size:11px;color:#abb9c9;line-height:1.65;margin:0}
	.link-button{color:#f0a1b2;background:transparent;border:0;cursor:pointer;font-size:11px;padding:8px 0}
	.readonly,.loading{margin:19px;padding:18px;color:#b1bed0;font-size:12px;line-height:1.75;background:#192536;border-left:3px solid #94704e}
	.note-row{border-top:1px solid #2c3e50;padding:16px 0}
	.note-row strong{font-size:12px}.note-row small{font-size:10px;color:#8da5b9;display:block;margin:7px 0}
	.note-row p{font-size:12px;color:#b6c6d7;line-height:1.75;overflow-wrap:anywhere;white-space:pre-wrap}
	.empty-inline{color:#a9b8ca;font-size:11px;padding:18px 0}
	.note-form{margin-top:16px;border-top:1px solid #31475a;padding-top:18px}
	.note-form label,.form-grid label{color:#abc0d3;font-size:11px;font-weight:750;display:flex;flex-direction:column;gap:9px}
	.note-form textarea,.form-grid select{width:100%;background:#0c1521;color:#f1f5fa;border:1px solid #395166;border-radius:6px;padding:12px;font-size:12px;font-family:inherit}
	.note-form textarea{margin:12px 0;resize:vertical}
	.form-footer{display:flex;justify-content:space-between;align-items:center;gap:12px}
	.form-footer small{font-size:10px;color:#91a7ba}
	.decision-card{background:#101d2e;border:1px solid #2d4257;border-radius:8px;padding:19px}
	.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px;margin:0 0 17px}
	.decision-card p{margin-bottom:14px}
	.response-cta{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:18px;background:#172639;border:1px solid #3b5268;border-radius:8px}
	.response-cta strong{font-size:14px}.response-cta p{color:#aebfd1;font-size:11px;line-height:1.7;margin:8px 0 0}
	.response-cta button{flex-shrink:0}
	.feedback{margin:14px 20px;border:1px solid #3c6b69;background:#1b3030;color:#b9e1d1;padding:14px;border-radius:7px;font-size:11px}
	.feedback.error{background:#332631;border-color:#95536b;color:#f4becb}
	.disclaimer{padding:15px 20px;border-top:1px solid #2c4052;background:#172334;color:#879db0;font-size:10px;font-weight:750;letter-spacing:.06em}
	@media(max-width:900px){.next-step,.response-cta{flex-direction:column;align-items:flex-start}.case-heading{flex-direction:column}.facts{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr}}
	@media(max-width:550px){.stage-tabs button{font-size:10px;padding:12px 4px}.stage-number{display:block;margin:0 0 6px}.stage-body{padding:14px}.asset-row,.form-footer{flex-direction:column;align-items:flex-start}}
</style>
