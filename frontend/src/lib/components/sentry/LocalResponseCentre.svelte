<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { chooseLabTenant, visibleLabTenants } from '$lib/sentry-lab/scope';
	import type { LabCase, LabIdentity, LabTenant } from '$lib/sentry-lab/scope';

	export let selectedTenantId: string;
	export let preferredIncidentId = '';
	export let csrf: string;
	export let labSessionUser: string;
	export let onOpenApiLab: () => void;
	export let onOpenCase: (tenantId: string, caseId: string) => void;

	type Playbook = {
		id: string; name: string; purpose: string; impact: string;
		steps: string[]; responseClass: string; executable: false; dryRunOnly: true;
	};
	type Proposal = {
		id: string; tenantId: string; incidentId: string; playbookId: string;
		playbookName: string; reason: string; status: 'pending'|'approved_dry_run'|'rejected';
		version: number; requestedBy: string; requestedAt: string;
		reviewedBy: string | null; reviewedAt: string | null;
		liveExecution: false; dryRunRecorded: boolean;
	};
	type History = {actor: string; action: string; reason: string; version: number; at: string};
	const API = 'http://127.0.0.1:8001';

	let identity = '';
	let membership: LabIdentity['memberships'] = [];
	let tenants: LabTenant[] = [];
	let incidents: LabCase[] = [];
	let playbooks: Playbook[] = [];
	let requests: Proposal[] = [];
	let history: History[] = [];

	let selectedId = '';
	let online = false;
	let loading = false;
	let busy = false;
	let error = '';
	let success = '';
	let showProposalForm = false;
	let showHistory = false;
	let filter: 'pending' | 'all' = 'pending';
	let proposalIncident = '';
	let proposalPlaybook = 'identity_review';
	let proposalReason = '';
	let decision: 'approve_dry_run' | 'reject' = 'approve_dry_run';
	let reviewReason = '';
	let pendingKey = '';
	let cycle = 0;
	let historyCycle = 0;
	let disposed = false;

	$: role = membership.find((member) => member.tenantId === selectedTenantId)?.role ?? '';
	$: isAnalyst = role === 'soc_analyst' || role === 'soc_lead';
	$: isLead = role === 'soc_lead';
	$: canWrite = isAnalyst && identity === labSessionUser && Boolean(csrf);
	$: canDecide = isLead && canWrite;
	$: shownRequests = filter === 'pending' ? requests.filter((item) => item.status === 'pending') : requests;
	$: selected = requests.find((item) => item.id === selectedId) ?? null;
	$: currentPlaybook = playbooks.find((item) => item.id === selected?.playbookId) ?? null;
	$: pendingCount = requests.filter((item) => item.status === 'pending').length;
	$: recordedCount = requests.filter((item) => item.dryRunRecorded).length;
	$: nextAction = !identity ? 'Sign in through API Lab' :
		!selected ? 'Choose a proposal or create a new one' :
		selected.status === 'pending' && canDecide && selected.requestedBy !== identity
			? 'Review the case evidence, then approve the dry-run or reject'
			: selected.status === 'pending' ? 'Await an independent SOC lead decision' :
		selected.status === 'approved_dry_run' && !selected.dryRunRecorded
			? 'Record the approved simulation receipt — no real action will run'
			: 'Decision recorded. Review the history or return to the case';

	function path(suffix: string) {
		return '/api/tenants/' + encodeURIComponent(selectedTenantId) + '/lab/' + suffix;
	}
	async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
		const response = await fetch(API + endpoint, {
			...options, credentials: 'include', cache: 'no-store',
			headers: {Accept: 'application/json', 'Content-Type':'application/json', ...(options.headers ?? {})},
		});
		if (!response.ok) {
			let detail = 'HTTP ' + response.status;
			try {
				const body = await response.json();
				if (typeof body.detail === 'string') detail += ': ' + body.detail;
			} catch { /* Keep generic HTTP error. */ }
			throw new Error(detail);
		}
		return (await response.json()) as T;
	}
	async function refreshRequests(preferredId?: string) {
		const generation = ++cycle;
		const tenant = selectedTenantId;
		const priorId = preferredId ?? selectedId;
		requests = [];
		selectedId = '';
		history = [];
		error = '';
		if (!tenant) return;
		try {
			const result = await request<{tenantId:string; liveExecution:false;items:Proposal[]}>(
				path('response-requests'));
			if (disposed || tenant !== selectedTenantId || generation !== cycle) return;
			if (result.tenantId !== tenant || result.liveExecution !== false ||
				result.items.some((item) => item.tenantId !== tenant || item.liveExecution !== false)) {
				throw new Error('Wrong organisation or provenance from the API. Response records withheld.');
			}
			requests = result.items;
			const visible = filter === 'pending'
				? requests.filter((item) => item.status === 'pending') : requests;
			selectedId = visible.some((item) => item.id === priorId)
				? priorId : (visible[0]?.id ?? '');
			if (selectedId) await refreshHistory();
		} catch (err) {
			if (disposed || generation !== cycle) return;
			requests = [];
			selectedId = '';
			error = err instanceof Error ? err.message : 'Response queue unavailable.';
		}
	}
	async function refreshHistory() {
		const generation = ++historyCycle;
		const tenant = selectedTenantId;
		const id = selectedId;
		history = [];
		if (!tenant || !id) return;
		try {
			const value = await request<{tenantId:string;requestId:string;items:History[]}>(
				path('response-requests/' + encodeURIComponent(id) + '/history'));
			if (disposed || generation !== historyCycle || tenant !== selectedTenantId || id !== selectedId) return;
			if (value.tenantId !== tenant || value.requestId !== id) throw new Error('History scope mismatch.');
			history = value.items;
		} catch (err) {
			if (disposed || generation !== historyCycle) return;
			error = err instanceof Error ? err.message : 'Cannot load response history.';
		}
	}
	async function connect() {
		const generation = ++cycle;
		const preferred = selectedTenantId;
		loading = true;
		online = false;
		identity = '';
		membership = [];
		tenants = [];
		requests = [];
		incidents = [];
		playbooks = [];
		selectedId = '';
		error = '';
		success = '';
		try {
			const health = await request<{service:string;mode:string;liveSensors:number}>('/api/health');
			if (health.service !== 'rh-sentry-lab' || health.mode !== 'synthetic-local-only'
				|| health.liveSensors !== 0) {
				throw new Error('Not the isolated fictional RH Sentry lab API.');
			}
			online = true;
			const [who, tenantList] = await Promise.all([
				request<LabIdentity>('/api/me'),
				request<{items:LabTenant[]}>('/api/tenants'),
			]);
			if (disposed || generation !== cycle) return;
			identity = who.user;
			membership = who.memberships;
			tenants = visibleLabTenants(tenantList.items,
				who.memberships.filter((entry) => entry.role === 'soc_analyst' || entry.role === 'soc_lead'));
			selectedTenantId = chooseLabTenant(tenants, preferred);
			if (selectedTenantId) await loadCustomer();
		} catch (err) {
			if (disposed || generation !== cycle) return;
			error = err instanceof Error ? err.message : 'Unable to connect to local response API.';
			identity = '';
			selectedTenantId = '';
			requests = [];
		} finally {
			if (!disposed) loading = false;
		}
	}
	async function loadCustomer() {
		const tenant = selectedTenantId;
		const generation = ++cycle;
		++historyCycle;
		incidents = [];
		playbooks = [];
		requests = [];
		selectedId = '';
		proposalIncident = '';
		error = '';
		success = '';
		if (!tenant) return;
		try {
			const [cases, templates] = await Promise.all([
				request<{tenantId:string;items:LabCase[]}>(
					'/api/tenants/' + encodeURIComponent(tenant) + '/incidents'),
				request<{tenantId:string;items:Playbook[];liveExecution:false}>(
					path('response-playbooks')),
			]);
			if (disposed || generation !== cycle || tenant !== selectedTenantId) return;
			if (cases.tenantId !== tenant || templates.tenantId !== tenant ||
				templates.liveExecution !== false || cases.items.some((item) => item.tenantId !== tenant) ||
				templates.items.some((item) => item.executable !== false || item.dryRunOnly !== true)) {
				throw new Error('Unexpected customer scope or live action capability.');
			}
			incidents = cases.items;
			playbooks = templates.items;
			const fromCase = incidents.some((item) => item.id === preferredIncidentId);
			proposalIncident = fromCase ? preferredIncidentId : (incidents[0]?.id ?? '');
			proposalPlaybook = playbooks[0]?.id ?? '';
			if (fromCase && canWrite) showProposalForm = true;
			await refreshRequests();
		} catch (err) {
			if (disposed || generation !== cycle) return;
			error = err instanceof Error ? err.message : 'Cannot load fictional response data.';
		}
	}
	function changeTenant() {
		showProposalForm = false;
		filter = 'pending';
		void loadCustomer();
	}
	function setFilter(next: 'pending' | 'all') {
		filter = next;
		const visible = next === 'pending'
			? requests.filter((item) => item.status === 'pending') : requests;
		if (!visible.some((item) => item.id === selectedId)) {
			selectRequest(visible[0]?.id ?? '');
		}
	}
	function selectRequest(id: string) {
		selectedId = id;
		reviewReason = '';
		showHistory = false;
		void refreshHistory();
	}
	async function propose() {
		if (!canWrite || busy || !proposalIncident || !proposalPlaybook || proposalReason.trim().length < 15) return;
		busy = true;
		error = '';
		success = '';
		if (!pendingKey) pendingKey = 'resp-' + crypto.randomUUID().replaceAll('-','');
		try {
			const result = await request<Proposal & {replayed:boolean}>(path('response-requests'), {
				method: 'POST', headers:{'X-CSRF-Token':csrf},
				body: JSON.stringify({
					incidentId: proposalIncident, playbookId: proposalPlaybook,
					reason: proposalReason.trim(), idempotencyKey: pendingKey,
				}),
			});
			pendingKey = '';
			showProposalForm = false;
			proposalReason = '';
			filter = 'pending';
			await refreshRequests(result.id);
			success = 'Response proposal saved. An independent SOC lead must decide before any simulation.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save proposal.';
			if (error.includes('409')) pendingKey = '';
		} finally {busy = false;}
	}
	async function decide() {
		const proposal = selected;
		if (!proposal || !canDecide || busy || proposal.requestedBy === identity ||
			reviewReason.trim().length < 15) return;
		busy = true;
		error = '';
		success = '';
		try {
			await request(path('response-requests/' + encodeURIComponent(proposal.id) + '/decision'), {
				method:'POST', headers:{'X-CSRF-Token':csrf},
				body: JSON.stringify({
					expectedVersion:proposal.version, decision, reason:reviewReason.trim(),
				}),
			});
			filter = 'all';
			reviewReason = '';
			await refreshRequests(proposal.id);
			success = 'Independent decision recorded. This authorises a fictional dry-run only.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save lead decision.';
			if (error.includes('409')) await refreshRequests(proposal.id);
		} finally {busy = false;}
	}
	async function simulate() {
		const proposal = selected;
		if (!proposal || !canDecide || busy || proposal.status !== 'approved_dry_run'
			|| proposal.dryRunRecorded) return;
		busy = true;
		error = '';
		success = '';
		try {
			const receipt = await request<{externalActions:number;liveExecution:false;result:string}>(
				path('response-requests/' + encodeURIComponent(proposal.id) + '/simulate'), {
					method:'POST',headers:{'X-CSRF-Token':csrf},
					body:JSON.stringify({expectedVersion:proposal.version}),
				});
			if (receipt.externalActions !== 0 || receipt.liveExecution !== false)
				throw new Error('Unexpected execution result; halt local testing.');
			await refreshRequests(proposal.id);
			success = 'Dry-run receipt recorded. No endpoint contacted and no live action executed.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Cannot record dry-run receipt.';
			if (error.includes('409')) await refreshRequests(proposal.id);
		} finally {busy = false;}
	}
	onMount(() => { void connect(); });
	onDestroy(() => {disposed = true; ++cycle; ++historyCycle;});
</script>

<div class="response-lab">
	<div class="safety">
		<div aria-hidden="true" class="symbol">✓</div>
		<div>
			<strong>Response decisions, without risk to customers.</strong>
			<p>Three steps: propose → independent lead decision → dry-run receipt. All records are fictional, and no real response action can run.</p>
		</div>
		<span class="safety-label">EXECUTION DISABLED</span>
	</div>
	<div class="page-tools">
		<div><span class="eyebrow">RH SENTRY / CONTROLLED RESPONSE</span><h2>Response work queue</h2>
			<p>{identity ? 'Signed in: ' + identity : 'Sign in to work on a case'} · no live integrations</p></div>
		<div class="buttons">
			{#if canWrite}<button type="button" class="primary" aria-expanded={showProposalForm} on:click={() => (showProposalForm = !showProposalForm)}>{showProposalForm ? 'Close form' : '+ Propose response'}</button>{/if}
			<button type="button" class="secondary" on:click={() => void connect()} disabled={busy || loading}>Refresh</button>
			<button type="button" class="secondary" on:click={onOpenApiLab}>API Lab</button>
		</div>
	</div>
	{#if loading}
		<div class="empty">Checking your local session and loading response work...</div>
	{:else if !identity || !tenants.length}
		<div class="empty"><strong>Start with an analyst session</strong><p>Open API Lab and sign in as a fictional SOC analyst or lead. Customer viewer accounts cannot access the internal response queue.</p>
			<button type="button" class="primary" on:click={onOpenApiLab}>Open API Lab →</button></div>
	{:else}
		<div class="customer-bar"><label for="response-customer">CUSTOMER</label>
			<select id="response-customer" bind:value={selectedTenantId} disabled={busy} on:change={changeTenant}>
				{#each tenants as tenant (tenant.id)}<option value={tenant.id}>{tenant.name}</option>{/each}
			</select>
			<span><strong>{pendingCount}</strong> awaiting lead decision · <strong>{recordedCount}</strong> recorded dry-runs</span>
		</div>
		{#if showProposalForm && canWrite}
			<form class="create-panel" on:submit|preventDefault={() => void propose()}>
				<span class="eyebrow">STEP 1 / PROPOSE</span>
				<h3>Create a response proposal</h3>
				<p>Use an existing fictional incident. An approved request cannot execute a response.</p>
				<div class="form-grid">
					<label>Incident<select bind:value={proposalIncident} required>
						{#each incidents as incident (incident.id)}
							<option value={incident.id}>{incident.id} · {incident.title}</option>
						{/each}
					</select></label>
					<label>Playbook<select bind:value={proposalPlaybook} required>
						{#each playbooks as playbook (playbook.id)}<option value={playbook.id}>{playbook.name}</option>{/each}
					</select></label>
					<label class="full">Why is this proposed?
						<textarea rows="3" bind:value={proposalReason} minlength="15" maxlength="500" required placeholder="Describe the evidence and reason for independent review..."></textarea>
					</label>
				</div>
				<button class="primary" type="submit" disabled={busy || proposalReason.trim().length < 15}>Save and request review</button>
			</form>
		{/if}
		<div class="workspace">
			<section class="panel queue" aria-label="Fictional response proposals">
				<div class="section-head">
					<div><span class="eyebrow">STEP 2 / REVIEW</span><h3>Work queue</h3></div>
					<div class="filters">
						<button type="button" class:active={filter === 'pending'} on:click={() => setFilter('pending')}>Needs decision</button>
						<button type="button" class:active={filter === 'all'} on:click={() => setFilter('all')}>All</button>
					</div>
				</div>
				{#each shownRequests as proposal (proposal.id)}
					<button class="queue-row" type="button" class:selected={selectedId === proposal.id}
						aria-pressed={selectedId === proposal.id} on:click={() => selectRequest(proposal.id)}>
						<span>{proposal.incidentId}<small>{proposal.status.replaceAll('_',' ')}</small></span>
						<strong>{proposal.playbookName}</strong>
						<small>Requested by {proposal.requestedBy}</small>
					</button>
				{:else}
					<div class="empty-inline">{filter === 'pending' ? 'Nothing awaiting a decision. Create a proposal or view all records.' : 'No response proposals yet. Start with a fictional incident.'}</div>
				{/each}
			</section>
			<section class="panel detail" aria-label="Next response task">
				<div class="section-head">
					<span class="eyebrow">CLEAR NEXT STEP</span>
					<h3>{selected ? selected.playbookName : 'Choose a response proposal'}</h3>
					<p class="instruction">{nextAction}</p>
				</div>
				{#if selected}
					<div class="detail-body">
						<div class="key-values">
							<div><span>INCIDENT</span><button type="button" on:click={() => onOpenCase(selectedTenantId, selected.incidentId)}>{selected.incidentId} →</button></div>
							<div><span>STATUS</span><strong>{selected.status.replaceAll('_',' ')}</strong></div>
							<div><span>REQUESTED BY</span><strong>{selected.requestedBy}</strong></div>
							<div><span>LIVE ACTIONS</span><strong>None</strong></div>
						</div>
						<h4>Evidence and rationale</h4>
						<p>{selected.reason}</p>
						{#if currentPlaybook}
							<details class="checklist">
								<summary>Review the playbook and impact</summary>
								<p>{currentPlaybook.impact}</p>
								<ol>{#each currentPlaybook.steps as step}<li>{step}</li>{/each}</ol>
							</details>
						{/if}
						{#if selected.status === 'pending'}
							{#if canDecide && selected.requestedBy !== identity}
								<form class="decision" on:submit|preventDefault={() => void decide()}>
									<h4>Independent lead decision</h4>
									<label>Decision<select bind:value={decision}>
										<option value="approve_dry_run">Approve for dry-run only</option>
										<option value="reject">Reject proposal</option>
									</select></label>
									<label>Reason<textarea rows="3" bind:value={reviewReason} minlength="15" maxlength="500" required placeholder="Document the evidence, scope and business impact..."></textarea></label>
									<button type="submit" class="primary" disabled={busy || reviewReason.trim().length < 15}>Record lead decision</button>
								</form>
							{:else if selected.requestedBy === identity}
								<div class="waiting">Waiting for a different SOC lead. You cannot approve your own proposal.</div>
							{:else}
								<div class="waiting">Independent SOC lead review is required. Ask the lead to sign in through API Lab.</div>
							{/if}
						{:else if selected.status === 'approved_dry_run' && !selected.dryRunRecorded}
							<div class="decision">
								<h4>STEP 3 / RECORD SIMULATION</h4>
								<p>Saving a dry-run receipt will not execute the planned action or contact endpoints.</p>
								{#if canDecide}<button type="button" class="primary" disabled={busy} on:click={simulate}>Record dry-run receipt</button>
								{:else}<p class="waiting">A SOC lead must record the dry-run receipt.</p>{/if}
							</div>
						{:else if selected.dryRunRecorded}
							<div class="complete">✓ Dry-run receipt recorded. No real action occurred.</div>
						{:else}
							<div class="waiting">Rejected proposal. No action performed.</div>
						{/if}
						<div class="history-head">
							<button class="secondary" type="button" aria-expanded={showHistory} on:click={() => (showHistory = !showHistory)}> {showHistory ? 'Hide' : 'View'} decision history</button>
						</div>
						{#if showHistory}
							<ol class="timeline">
								{#each history as event, i (i)}
									<li><strong>{event.action.replaceAll('_',' ')}</strong><small>{event.actor} · {event.at}</small><p>{event.reason}</p></li>
								{:else}<li>No saved decisions yet.</li>{/each}
							</ol>
						{/if}
					</div>
				{:else}
					<div class="empty-inline">Select a pending proposal, or use “+ Propose response” to start from a fictional incident.</div>
				{/if}
			</section>
		</div>
	{/if}
	{#if success}<p class="feedback" role="status">{success}</p>{/if}
	{#if error}<p class="feedback error" role="alert">{error}</p>{/if}
	<p class="footnote">RH SENTRY · LOCAL FICTIONAL WORKFLOW · TWO-PERSON APPROVAL FOR DRY-RUN · ZERO EXECUTABLE RESPONSE CONNECTORS</p>
</div>

<style>
	.response-lab{color:#e9f0f8}
	.safety{background:linear-gradient(110deg,#2a2431,#151d28);border:1px solid #75505f;border-radius:9px;padding:18px;display:flex;gap:15px;align-items:center;margin-bottom:20px}
	.symbol{width:43px;height:43px;border:1px solid #8d6270;border-radius:8px;display:grid;place-items:center;color:#e8889c;font-size:23px;flex-shrink:0}
	.safety strong{font-size:14px}.safety p{font-size:11px;color:#a7b9ca;margin:6px 0 0;line-height:1.65}
	.safety-label{color:#d9c0a7;border:1px solid #88684a;padding:8px;font-size:10px;border-radius:5px;white-space:nowrap;margin-left:auto;font-weight:800}
	.page-tools{display:flex;justify-content:space-between;align-items:center;gap:16px;margin:24px 0}
	.page-tools h2{font-size:24px;margin:7px 0}.page-tools p{font-size:11px;color:#9eb1c5}
	.eyebrow{font-size:10px;letter-spacing:.12em;color:#e36c83;font-weight:800}
	.buttons{display:flex;gap:8px;flex-wrap:wrap}
	.primary,.secondary{border:1px solid #78526a;background:#312633;color:#efc0cb;font-size:11px;font-weight:750;padding:11px 13px;border-radius:6px;cursor:pointer}
	.primary{background:#dc3854;border-color:#ed4e68;color:white}
	button:disabled{opacity:.4;cursor:not-allowed}
	.customer-bar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:#172333;border:1px solid #35465a;border-radius:8px;padding:13px 16px;margin-bottom:17px}
	.customer-bar label,.customer-bar span{font-size:11px;color:#a6b8ca}.customer-bar label{font-weight:800}
	.customer-bar span{margin-left:auto}
	select,input,textarea{background:#0a1420;color:#e8f1f9;border:1px solid #3c4d60;border-radius:6px;font-size:12px;padding:10px 12px;width:100%;min-width:0}
	.customer-bar select{width:auto;min-width:190px}
	.create-panel{border:1px solid #37495e;border-radius:9px;background:#131e2d;padding:20px;margin-bottom:18px}
	.create-panel h3{font-size:18px;margin:8px 0}.create-panel p{font-size:11px;color:#9db1c6;line-height:1.65}
	.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:18px 0}
	.form-grid label,.decision label{display:flex;flex-direction:column;gap:8px;font-size:11px;color:#acbfce;font-weight:750}
	.form-grid label.full{grid-column:1/-1}
	.workspace{display:grid;grid-template-columns:minmax(245px,.85fr) minmax(390px,1.6fr);gap:15px;align-items:start}
	.panel{border:1px solid #304156;background:#121c29;border-radius:9px;overflow:hidden;min-width:0}
	.section-head{padding:19px;border-bottom:1px solid #2e3e51}
	.section-head h3{font-size:17px;margin:9px 0}
	.filters{display:flex;gap:6px;margin-top:13px}
	.filters button{background:#1b2a3b;border:1px solid #384b5d;color:#b8cadd;padding:9px 10px;border-radius:5px;cursor:pointer;font-size:11px}
	.filters button.active{background:#49303d;border-color:#ac5169;color:#fff}
	.queue-row{border:0;border-top:1px solid #2a3b4c;background:transparent;color:#ecf2f9;text-align:left;display:flex;flex-direction:column;gap:9px;padding:16px;width:100%;cursor:pointer}
	.queue-row:hover,.queue-row.selected{background:#302530;box-shadow:inset 3px 0 #de4a63}
	.queue-row span{display:flex;justify-content:space-between;gap:10px;color:#f5a4b4;font-size:11px}
	.queue-row strong{font-size:13px}
	.queue-row small{font-size:10px;color:#9db2c6;font-weight:400}
	.instruction{color:#efbbca;font-size:12px;line-height:1.7;margin:12px 0 0;font-weight:650}
	.detail-body{padding:19px}
	.detail-body h4{font-size:14px;margin:18px 0 9px}
	.detail-body p{font-size:12px;color:#adbed0;line-height:1.75;overflow-wrap:anywhere}
	.key-values{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
	.key-values>div{display:flex;flex-direction:column;gap:9px;border:1px solid #2c3e52;border-radius:6px;padding:12px}
	.key-values span{color:#92a8c1;font-size:10px;font-weight:800}
	.key-values strong,.key-values button{font-size:12px;color:#ecf2fa;text-align:left}
	.key-values button{border:0;background:transparent;color:#f39aaf;cursor:pointer;padding:0}
	.checklist{background:#152338;border:1px solid #31475b;border-radius:7px;padding:13px 15px;margin:15px 0}
	.checklist summary{color:#d6e5f4;font-size:12px;font-weight:750;cursor:pointer}
	.checklist ol{color:#b0c1d2;font-size:11px;line-height:1.9;padding-left:20px}
	.decision{background:#172638;border:1px solid #365267;border-radius:7px;padding:15px;margin-top:16px}
	.decision label{margin:12px 0}
	.waiting,.complete{padding:14px;border-left:3px solid #b58a66;background:#292831;color:#eac4a7;font-size:11px;line-height:1.7;margin-top:15px}
	.complete{border-color:#5c9c86;color:#b8ebd3;background:#1b302f}
	.history-head{margin-top:18px}
	.timeline{border-top:1px solid #324559;padding:15px 0 0 18px;font-size:11px;color:#aebfd0}
	.timeline li{margin:11px 0}.timeline strong{font-size:12px;color:#e5edf5}.timeline small{display:block;font-size:10px;margin:5px 0;color:#9eb2c8}
	.empty,.empty-inline{padding:21px;color:#adc0d2;font-size:12px;line-height:1.7;background:#192739;border:1px solid #34495b;border-radius:7px}
	.empty strong{color:#e8f1f9}.empty p{font-size:12px}
	.empty-inline{background:transparent;border:0}
	.feedback{padding:14px;margin:18px 0;font-size:12px;border:1px solid #3e7869;border-radius:7px;background:#1c3332;color:#b2decf}
	.feedback.error{background:#322632;border-color:#985365;color:#f2b4c1}
	.footnote{font-size:10px;color:#8298ac;margin:18px 0;padding-top:14px;border-top:1px solid #304255}
	@media(max-width:1060px){.workspace{grid-template-columns:1fr}.page-tools,.safety{flex-direction:column;align-items:flex-start}.safety-label{margin-left:0}}
	@media(max-width:600px){.form-grid,.key-values{grid-template-columns:1fr}.form-grid label.full{grid-column:1}.customer-bar select{width:100%}}
</style>
