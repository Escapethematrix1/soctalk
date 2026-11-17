<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { chooseLabTenant, visibleLabTenants } from '$lib/sentry-lab/scope';
	import type { LabIdentity, LabTenant } from '$lib/sentry-lab/scope';

	export let selectedTenantId: string;
	export let csrf: string;
	export let labSessionUser: string;
	export let onOpenApiLab: () => void;
	export let onOpenPipeline: () => void;

	type Strategy = 'identity_travel' | 'encoded_powershell' | 'wazuh_ssh_burst';
	type Status = 'draft' | 'test_enabled' | 'disabled';
	type Disposition = 'unreviewed' | 'false_positive' | 'needs_investigation';
	type Template = {
		strategy: Strategy; title: string; description: string; threshold: number;
		minThreshold: number; maxThreshold: number; thresholdUnit: string;
	};
	type Rule = {
		id: string; tenantId: string; title: string; description: string;
		strategy: Strategy; status: Status; threshold: number; version: number;
		minThreshold: number; maxThreshold: number; thresholdUnit: string;
		updatedAt: string; liveDetection: false;
	};
	type Batch = {id: number; scenarioId: string; createdAt: string; eventCount: number};
	type Run = {
		id: number; tenantId: string; ruleId: string; ruleVersion: number;
		strategy: Strategy; threshold: number; batchId: number;
		outcome: 'matched' | 'not_matched'; matchedEventIds: number[];
		eventCount: number; testedBy: string; testedAt: string;
		liveDetection: false;
	};
	type Finding = {
		id: number; tenantId: string; runId: number; ruleId: string;
		batchId: number; ruleVersion: number; matchedEventIds: number[];
		disposition: Disposition; version: number; reviewedBy: string | null;
		reviewedAt: string | null; testedAt: string; liveDetection: false;
	};
	type History = {actor: string; action: string; detail: string; version: number; occurred_at: string};
	type ReviewHistory = {actor: string; disposition: string; reason: string; version: number; reviewed_at: string};

	const API = 'http://127.0.0.1:8001';
	let identity = '';
	let memberships: LabIdentity['memberships'] = [];
	let tenants: LabTenant[] = [];
	let templates: Template[] = [];
	let rules: Rule[] = [];
	let batches: Batch[] = [];
	let runs: Run[] = [];
	let findings: Finding[] = [];
	let ruleHistory: History[] = [];
	let findingHistory: ReviewHistory[] = [];

	let selectedRuleId = '';
	let selectedBatchId = 0;
	let selectedFindingId = 0;
	let online = false;
	let loading = false;
	let busy = false;
	let failure = '';
	let message = '';
	let selectionGeneration = 0;
	let detailGeneration = 0;
	let destroyed = false;
	let pendingTestKey = '';

	let editTitle = '';
	let editDescription = '';
	let editThreshold = 500;
	let editStatus: Status = 'draft';

	let newOpen = false;
	let newStrategy: Strategy = 'identity_travel';
	let newTitle = '';
	let newDescription = '';
	let newThreshold = 500;
	let reviewDisposition: 'false_positive' | 'needs_investigation' = 'false_positive';
	let reviewReason = '';

	$: activeRole = memberships.find((member) => member.tenantId === selectedTenantId)?.role ?? '';
	$: authorised = activeRole === 'soc_analyst' || activeRole === 'soc_lead';
	$: canWrite = authorised && identity === labSessionUser && Boolean(csrf);
	$: selected = rules.find((rule) => rule.id === selectedRuleId) ?? null;
	$: selectedFinding = findings.find((item) => item.id === selectedFindingId) ?? null;
	$: template = templates.find((item) => item.strategy === newStrategy) ?? null;
	$: edits = Boolean(selected && (
		editTitle !== selected.title || editDescription !== selected.description ||
		editThreshold !== selected.threshold || editStatus !== selected.status
	));
	$: positives = runs.filter((item) => item.outcome === 'matched').length;
	$: unreviewed = findings.filter((item) => item.disposition === 'unreviewed').length;

	function scope(extra: string): string {
		return '/api/tenants/' + encodeURIComponent(selectedTenantId) + '/lab/' + extra;
	}
	async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
		const response = await fetch(API + path, {
			...init, credentials: 'include', cache: 'no-store',
			headers: { 'Content-Type':'application/json', ...(init.headers ?? {}) },
		});
		if (!response.ok) {
			let description = 'HTTP ' + response.status;
			try {
				const body = await response.json();
				if (typeof body.detail === 'string') description += ': ' + body.detail;
			} catch { /* No trusted JSON error body. */ }
			throw new Error(description);
		}
		return await response.json() as T;
	}
	function editFrom(rule: Rule) {
		editTitle = rule.title;
		editDescription = rule.description;
		editThreshold = rule.threshold;
		editStatus = rule.status;
	}
	function clearTenantData() {
		rules = []; batches = []; runs = []; findings = []; templates = [];
		ruleHistory = []; findingHistory = []; selectedRuleId = '';
		selectedFindingId = 0; selectedBatchId = 0; pendingTestKey = '';
	}
	async function loadRuleHistory() {
		const serial = ++detailGeneration;
		const tenant = selectedTenantId;
		const ruleId = selectedRuleId;
		ruleHistory = [];
		if (!tenant || !ruleId) return;
		try {
			const result = await api<{tenantId:string; ruleId:string; items:History[]}>(
				scope('detection-rules/' + encodeURIComponent(ruleId) + '/history'));
			if (destroyed || serial !== detailGeneration || tenant !== selectedTenantId ||
				ruleId !== selectedRuleId) return;
			if (result.tenantId !== tenant || result.ruleId !== ruleId)
				throw new Error('Rule history scope mismatch.');
			ruleHistory = result.items;
		} catch (error) {
			if (!destroyed && serial === detailGeneration)
				failure = error instanceof Error ? error.message : 'Rule history unavailable.';
		}
	}
	async function loadFindingHistory() {
		const finding = selectedFinding;
		const tenant = selectedTenantId;
		findingHistory = [];
		if (!finding || !tenant) return;
		try {
			const result = await api<{tenantId:string; findingId:number; items:ReviewHistory[]}>(
				scope('detection-findings/' + finding.id + '/reviews'));
			if (!destroyed && tenant === selectedTenantId && selectedFindingId === finding.id &&
				result.tenantId === tenant && result.findingId === finding.id) {
				findingHistory = result.items;
			}
		} catch (error) {
			if (!destroyed) failure = error instanceof Error ? error.message : 'Review history unavailable.';
		}
	}
	async function loadWorkspace(preferredRule?: string) {
		const serial = ++selectionGeneration;
		const tenant = selectedTenantId;
		const existingRule = preferredRule ?? selectedRuleId;
		loading = true; failure = '';
		clearTenantData();
		if (!tenant) { loading = false; return; }
		try {
			const [types, ruleResponse, batchResponse, runResponse, findingResponse] = await Promise.all([
				api<{tenantId:string;items:Template[]}>(scope('detection-templates')),
				api<{tenantId:string;items:Rule[]}>(scope('detection-rules')),
				api<{tenantId:string;items:Batch[]}>(scope('event-batches')),
				api<{tenantId:string;items:Run[]}>(scope('detection-runs')),
				api<{tenantId:string;items:Finding[]}>(scope('detection-findings')),
			]);
			if (destroyed || serial !== selectionGeneration || tenant !== selectedTenantId) return;
			if ([types.tenantId,ruleResponse.tenantId,batchResponse.tenantId,
				runResponse.tenantId,findingResponse.tenantId].some((id) => id !== tenant)
				|| ruleResponse.items.some((item) => item.tenantId !== tenant || item.liveDetection !== false)
				|| runResponse.items.some((item) => item.tenantId !== tenant || item.liveDetection !== false)
				|| findingResponse.items.some((item) => item.tenantId !== tenant || item.liveDetection !== false)) {
				throw new Error('API returned data outside the selected fictional tenant; results withheld.');
			}
			templates = types.items;
			rules = ruleResponse.items;
			batches = batchResponse.items;
			runs = runResponse.items;
			findings = findingResponse.items;
			selectedRuleId = rules.some((rule) => rule.id === existingRule) ? existingRule : rules[0]?.id ?? '';
			selectedBatchId = batches[0]?.id ?? 0;
			const chosen = rules.find((rule) => rule.id === selectedRuleId);
			if (chosen) editFrom(chosen);
			await loadRuleHistory();
			if (findings.length) {
				selectedFindingId = findings[0].id;
				await loadFindingHistory();
			}
		} catch (error) {
			if (destroyed || serial !== selectionGeneration) return;
			clearTenantData();
			failure = error instanceof Error ? error.message : 'Could not fetch fictional detection workspace.';
		} finally {
			if (!destroyed && serial === selectionGeneration) loading = false;
		}
	}
	async function connect() {
		const preferred = selectedTenantId;
		online = false; identity = ''; memberships = []; tenants = [];
		selectedTenantId = ''; clearTenantData(); loading = true; failure = ''; message = '';
		try {
			const health = await api<{service:string;mode:string;liveSensors:number}>('/api/health');
			if (health.service !== 'rh-sentry-lab' || health.mode !== 'synthetic-local-only' ||
				health.liveSensors !== 0) throw new Error('Unexpected service identity; data withheld.');
			online = true;
			const [me, list] = await Promise.all([
				api<LabIdentity>('/api/me'), api<{items:LabTenant[]}>('/api/tenants'),
			]);
			if (destroyed) return;
			identity = me.user;
			memberships = me.memberships;
			const permitted = me.memberships.filter((member) =>
				member.role === 'soc_analyst' || member.role === 'soc_lead');
			tenants = visibleLabTenants(list.items, permitted);
			selectedTenantId = chooseLabTenant(tenants, preferred);
			if (selectedTenantId) await loadWorkspace();
			else failure = 'Detection Engineering requires an authorised fictional SOC analyst.';
		} catch (error) {
			if (destroyed) return;
			failure = error instanceof Error ? error.message : 'Unable to reach local API.';
			identity = ''; tenants = []; selectedTenantId = ''; clearTenantData();
		} finally { if (!destroyed) loading = false; }
	}
	function setRule(id: string) {
		selectedRuleId = id;
		pendingTestKey = '';
		const next = rules.find((rule) => rule.id === id);
		if (next) editFrom(next);
		void loadRuleHistory();
	}
	function changeTenant() {
		message = '';
		void loadWorkspace();
	}
	function changeBatch() { pendingTestKey = ''; }
	function resetTemplate() {
		const item = templates.find((choice) => choice.strategy === newStrategy);
		if (!item) return;
		newTitle = item.title + ' (training copy)';
		newDescription = item.description;
		newThreshold = item.threshold;
	}
	async function saveRule() {
		const rule = selected;
		if (!rule || !canWrite || !edits || busy) return;
		busy = true; failure = ''; message = '';
		try {
			const changes: Record<string, unknown> = {expectedVersion:rule.version};
			if (editTitle !== rule.title) changes.title = editTitle.trim();
			if (editDescription !== rule.description) changes.description = editDescription.trim();
			if (editThreshold !== rule.threshold) changes.threshold = editThreshold;
			if (editStatus !== rule.status) changes.status = editStatus;
			await api(scope('detection-rules/' + encodeURIComponent(rule.id)), {
				method:'PATCH', headers:{'X-CSRF-Token':csrf}, body:JSON.stringify(changes)
			});
			await loadWorkspace(rule.id);
			message = 'Versioned fictional detection rule saved. No live detector is connected.';
		} catch (err) {
			failure = err instanceof Error ? err.message : 'Rule update failed.';
			if (failure.includes('409')) await loadWorkspace(rule.id);
		} finally {busy = false;}
	}
	async function createRule() {
		if (!canWrite || busy) return;
		busy = true; failure = ''; message = '';
		try {
			const result = await api<Rule>(scope('detection-rules'), {
				method:'POST', headers:{'X-CSRF-Token':csrf},
				body:JSON.stringify({strategy:newStrategy,title:newTitle.trim(),
					description:newDescription.trim(),threshold:newThreshold})
			});
			newOpen = false;
			await loadWorkspace(result.id);
			message = 'Training rule draft created. It cannot execute actions or monitor endpoints.';
		} catch (err) {
			failure = err instanceof Error ? err.message : 'Could not create rule.';
		} finally {busy = false;}
	}
	async function testRule() {
		const rule = selected;
		if (!canWrite || !rule || !selectedBatchId || busy) return;
		busy = true; failure = ''; message = '';
		if (!pendingTestKey) pendingTestKey = 'rh-test-' + crypto.randomUUID().replaceAll('-','');
		try {
			const result = await api<Run & {replayed:boolean}>(
				scope('detection-rules/' + encodeURIComponent(rule.id) + '/test'), {
				method:'POST', headers:{'X-CSRF-Token':csrf},
				body:JSON.stringify({batchId:selectedBatchId,expectedVersion:rule.version,
					idempotencyKey:pendingTestKey})
			});
			pendingTestKey = '';
			await loadWorkspace(rule.id);
			message = (result.replayed ? 'Reused' : 'Saved') + ' synthetic test #' + result.id +
				': ' + result.outcome + ' (' + result.matchedEventIds.length + ' supporting event IDs).';
		} catch (err) {
			failure = err instanceof Error ? err.message : 'Synthetic rule test failed.';
			if (failure.includes('409')) pendingTestKey = '';
		} finally {busy = false;}
	}
	async function reviewFinding() {
		const finding = selectedFinding;
		if (!finding || !canWrite || busy) return;
		busy = true; failure = ''; message = '';
		try {
			await api(scope('detection-findings/' + finding.id + '/review'), {
				method:'POST', headers:{'X-CSRF-Token':csrf},
				body:JSON.stringify({expectedVersion:finding.version,
					disposition:reviewDisposition,reason:reviewReason.trim()})
			});
			reviewReason = '';
			const ruleId = selectedRuleId;
			await loadWorkspace(ruleId);
			message = 'Finding review recorded. No incident was created or modified.';
		} catch (err) {
			failure = err instanceof Error ? err.message : 'Unable to record analyst disposition.';
		} finally {busy = false;}
	}
	onMount(() => { void connect(); });
	onDestroy(() => { destroyed = true; ++selectionGeneration; ++detailGeneration; });
</script>

<div class="detections">
	<div class="lab-banner">
		<div class="banner-symbol" aria-hidden="true">◇</div>
		<div><strong>Versioned Detection Engineering · Fictional evidence only</strong>
			<p>Create and tune allowlisted detection rules, test stored synthetic batches and review findings. There is no live SIEM connection, autonomous analysis or automated response.</p></div>
		<span class:online class="status">{online ? 'LOCAL SQLITE LAB' : 'API OFFLINE'}</span>
	</div>
	<div class="metrics">
		<div><span>TRAINING RULES</span><strong>{rules.length.toString().padStart(2,'0')}</strong><small>Persisted definitions</small></div>
		<div><span>SYNTHETIC BATCHES</span><strong>{batches.length.toString().padStart(2,'0')}</strong><small>Eligible event fixtures</small></div>
		<div><span>MATCHED TEST RUNS</span><strong>{positives.toString().padStart(2,'0')}</strong><small>Not operational detections</small></div>
		<div><span>AWAITING HUMAN REVIEW</span><strong>{unreviewed.toString().padStart(2,'0')}</strong><small>Sample findings only</small></div>
	</div>
	<div class="heading">
		<div><span class="eyebrow">RED HORIZON / DETECTION OPERATIONS</span><h2>Rule engineering workbench</h2>
			<p>Signed-in fictional analyst: {identity || 'None'}. Live monitoring: 0 sources.</p></div>
		<div class="actions">
			{#if canWrite}<button class="primary" type="button" aria-expanded={newOpen} on:click={() => {newOpen = !newOpen; if(newOpen) resetTemplate();}}>{newOpen ? 'Close rule form' : '+ Create training rule'}</button>{/if}
			<button class="secondary" type="button" disabled={loading || busy} on:click={() => void connect()}>Refresh lab ↻</button>
			<button class="secondary" type="button" on:click={onOpenApiLab}>API Lab ↗</button>
		</div>
	</div>

	{#if loading}
		<div class="empty">Loading authorised synthetic detection data...</div>
	{:else if !identity || !tenants.length}
		<div class="empty"><strong>Fictional analyst session required</strong>
			<p>Sign in through API Lab as an authorised SOC analyst. Viewer roles cannot access detection rule internals or test findings.</p>
			<button class="primary" type="button" on:click={onOpenApiLab}>Open API Lab</button></div>
	{:else}
		<div class="tenant-selector"><label for="det-tenant">AUTHORISED ORGANISATION</label>
			<select id="det-tenant" bind:value={selectedTenantId} disabled={busy} on:change={changeTenant}>
				{#each tenants as tenant (tenant.id)}<option value={tenant.id}>{tenant.name}</option>{/each}
			</select><span>NO LIVE RULE EXECUTION</span></div>
		{#if newOpen && canWrite}
			<section class="panel creation">
				<div class="section-head"><span class="eyebrow">SAFE RULE BUILDER</span><h3>Create a fictional detection draft</h3></div>
				<div class="form-grid">
					<label>Strategy<select bind:value={newStrategy} on:change={resetTemplate}>
						{#each templates as item (item.strategy)}<option value={item.strategy}>{item.title}</option>{/each}
					</select></label>
					<label>Training title<input bind:value={newTitle} maxlength="90" placeholder="Fictional training rule"/></label>
					<label class="wide">Description<input bind:value={newDescription} maxlength="240"/></label>
					<label>Threshold<input type="number" bind:value={newThreshold} min={template?.minThreshold ?? 1} max={template?.maxThreshold ?? 5000} step="1"/></label>
				</div>
				<p class="muted">Only three built-in deterministic strategies are allowed. No arbitrary queries, scripts or commands are accepted. New rules begin as drafts.</p>
				<button class="primary" type="button" disabled={busy || newTitle.trim().length < 5} on:click={createRule}>Save rule draft</button>
			</section>
		{/if}
		<div class="workspace">
			<section class="panel rule-list">
				<div class="section-head"><span class="eyebrow">TENANT RULE CATALOGUE</span><h3>Detection definitions</h3></div>
				<div class="rule-items">
					{#each rules as item (item.id)}
						<button class:chosen={selectedRuleId===item.id} aria-pressed={selectedRuleId===item.id} type="button" on:click={() => setRule(item.id)}>
							<div class="line"><small>{item.id}</small><small>{item.status.replaceAll('_',' ')}</small></div>
							<strong>{item.title}</strong>
							<div class="meta">{item.strategy.replaceAll('_',' ')} · version {item.version}</div>
						</button>
					{:else}<div class="empty">No rules returned for this fictional tenant.</div>{/each}
				</div>
			</section>
			<section class="panel rule-detail">
				{#if selected}
					<div class="section-head"><span class="eyebrow">SELECTED RULE / {selected.id}</span><h3>{selected.title}</h3>
						<p>Version {selected.version} · {selected.thresholdUnit} · no live integration</p></div>
					<div class="rule-overview">
						<div><span>STRATEGY</span><strong>{selected.strategy.replaceAll('_',' ')}</strong></div>
						<div><span>STATE</span><strong>{selected.status.replaceAll('_',' ')}</strong></div>
						<div><span>RULE VERSION</span><strong>{selected.version}</strong></div>
						<div><span>LIVE ENFORCEMENT</span><strong>OFF</strong></div>
					</div>
					{#if canWrite}
						<div class="inner">
							<span class="eyebrow">VERSIONED RULE CONTROL</span><h4>Tune detection settings</h4>
							<div class="form-grid">
								<label>Title<input bind:value={editTitle} maxlength="90"/></label>
								<label>State<select bind:value={editStatus}><option value="draft">Draft</option><option value="test_enabled">Test enabled (manual only)</option><option value="disabled">Disabled</option></select></label>
								<label class="wide">Description<input bind:value={editDescription} maxlength="240"/></label>
								<label>Threshold · {selected.thresholdUnit}<input type="number" bind:value={editThreshold} min={selected.minThreshold} max={selected.maxThreshold} step="1"/></label>
							</div>
							<button class="primary" type="button" disabled={!edits || busy} on:click={saveRule}>Save versioned changes</button>
							<p class="muted">Manual tests preserve the exact version and threshold used. A disabled rule cannot be tested.</p>
						</div>
					{:else}<div class="inner">Sign in again through API Lab for an in-memory CSRF token to make changes.</div>{/if}
					<div class="inner history">
						<span class="eyebrow">RULE CHANGE JOURNAL</span>
						{#each ruleHistory as event, i (i)}
							<div class="journal-entry"><strong>{event.action} · v{event.version}</strong>
								<p>{event.detail} · {event.actor}</p><small>{event.occurred_at}</small></div>
						{:else}<p class="muted">No analyst changes to this rule yet.</p>{/each}
					</div>
				{:else}<div class="empty">Select a fictional detection definition to inspect and tune it.</div>{/if}
			</section>
		</div>
		<div class="workspace bottom">
			<section class="panel">
				<div class="section-head"><span class="eyebrow">CONTROLLED EVALUATION / MANUAL ONLY</span><h3>Test against stored event batch</h3>
					<p>Runs one versioned rule against an existing, tenant-owned synthetic batch.</p></div>
				<div class="inner">
					<label class="input-label" for="det-batch">SYNTHETIC EVENT BATCH
						<select id="det-batch" bind:value={selectedBatchId} disabled={busy} on:change={changeBatch}>
							{#each batches as batch (batch.id)}<option value={batch.id}>#{batch.id} · {batch.scenarioId} · {batch.eventCount} events</option>{/each}
						</select>
					</label>
					{#if !batches.length}
						<p class="muted">There are no stored event batches for this organisation. Generate one from Event Pipeline first.</p>
					{/if}
					<div class="actions">
						<button type="button" class="primary" disabled={!canWrite || busy || !selected || !batches.length || selected?.status === 'disabled'} on:click={testRule}>{busy ? 'Evaluating...' : 'Run synthetic rule test'}</button>
						<button type="button" class="secondary" on:click={onOpenPipeline}>Open Event Pipeline ↗</button>
					</div>
					<p class="muted">A match records its supporting synthetic event IDs for human review. No case, alert delivery or endpoint action is triggered.</p>
				</div>
				<div class="records">
					{#each runs as run (run.id)}
						<div class="record"><div class="line"><strong>Run #{run.id} · {run.ruleId}</strong><span class:positive={run.outcome==='matched'}>{run.outcome.replaceAll('_',' ')}</span></div>
							<p>Batch #{run.batchId} · Rule v{run.ruleVersion} · {run.eventCount} inspected events</p>
							<small>Matching IDs: {run.matchedEventIds.length ? run.matchedEventIds.join(', ') : 'none'} · {run.testedAt}</small></div>
					{:else}<div class="empty">No saved rule tests yet.</div>{/each}
				</div>
			</section>
			<section class="panel">
				<div class="section-head"><span class="eyebrow">FALSE-POSITIVE HANDLING</span><h3>Human finding review</h3>
					<p>Sample findings require analyst disposition; they are not confirmed threats.</p></div>
				<div class="findings">
					{#each findings as finding (finding.id)}
						<button type="button" class:chosen={selectedFindingId===finding.id} aria-pressed={selectedFindingId===finding.id} on:click={() => {selectedFindingId=finding.id; void loadFindingHistory();}}>
							<div class="line"><strong>Finding #{finding.id}</strong><span>{finding.disposition.replaceAll('_',' ')}</span></div>
							<small>{finding.ruleId} · Batch #{finding.batchId} · IDs {finding.matchedEventIds.join(', ')}</small>
						</button>
					{:else}<div class="empty">No synthetic findings awaiting review.</div>{/each}
				</div>
				{#if selectedFinding}
					<div class="inner">
						<span class="eyebrow">REVIEW SELECTED FINDING #{selectedFinding.id}</span>
						<p class="muted">Current disposition: {selectedFinding.disposition.replaceAll('_',' ')} · v{selectedFinding.version}</p>
						{#if canWrite}
							<div class="form-grid">
								<label>Review outcome<select bind:value={reviewDisposition}>
									<option value="false_positive">False positive (training)</option>
									<option value="needs_investigation">Needs human investigation</option>
								</select></label>
								<label class="wide">Review reason<textarea bind:value={reviewReason} maxlength="500" rows="3" placeholder="Record an evidence-grounded reason (minimum 12 characters)"></textarea></label>
							</div>
							<button type="button" class="primary" disabled={busy || reviewReason.trim().length < 12 || selectedFinding.disposition===reviewDisposition} on:click={reviewFinding}>Record review decision</button>
						{/if}
						<div class="history">
							{#each findingHistory as event, i (i)}
								<div class="journal-entry"><strong>{event.disposition.replaceAll('_',' ')} · v{event.version}</strong>
									<p>{event.reason}</p><small>{event.actor} · {event.reviewed_at}</small></div>
							{:else}<p class="muted">No review journal entries yet.</p>{/each}
						</div>
					</div>
				{/if}
			</section>
		</div>
	{/if}

	{#if failure}<div class="feedback error" role="alert">{failure}</div>{/if}
	{#if message}<div class="feedback" role="status">{message}</div>{/if}
	<footer>RH SENTRY / SYNTHETIC DETECTION ENGINEERING <span>NO LIVE SIEM · NO AGENT EXECUTION · NO AUTOMATIC CASES</span></footer>
</div>

<style>
	.detections{color:#edf2f9}
	.lab-banner{display:flex;align-items:center;gap:16px;padding:19px;border:1px solid #715060;border-radius:10px;background:linear-gradient(110deg,#302531,#151d29);margin-bottom:18px}
	.banner-symbol{display:grid;place-items:center;color:#efa1b3;border:1px solid #996074;border-radius:8px;font-size:25px;width:44px;height:44px;flex-shrink:0}
	.lab-banner strong{font-size:14px}.lab-banner p{font-size:12px;color:#acbbca;line-height:1.7;margin:7px 0 0}
	.status{border:1px solid #95704b;color:#ecc59a;border-radius:5px;font-size:10px;white-space:nowrap;padding:9px;margin-left:auto;font-weight:750}
	.status.online{color:#91d7b5;border-color:#548570}
	.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:21px}
	.metrics>div{border:1px solid #2e3e52;background:#121b28;border-radius:9px;padding:17px;display:flex;flex-direction:column;gap:9px}
	.metrics span{color:#95a9c1;font-size:10px;letter-spacing:.06em;font-weight:800}
	.metrics strong{font-size:27px}.metrics small{font-size:11px;color:#91a3b7}
	.heading{display:flex;justify-content:space-between;align-items:center;gap:17px;margin:24px 0}
	.heading h2{font-size:23px;margin:8px 0}.heading p{color:#91a5b9;font-size:12px;margin:0}
	.eyebrow{font-size:10px;font-weight:800;letter-spacing:.11em;color:#e66e82}
	.actions{display:flex;align-items:center;flex-wrap:wrap;gap:9px}
	.primary,.secondary{cursor:pointer;border:1px solid #70506a;border-radius:6px;padding:11px 14px;background:#352631;color:#f6c3cc;font-size:11px;font-weight:800}
	.primary{background:#dc3653;color:white;border-color:#f14c66}
	.primary:disabled,.secondary:disabled{opacity:.45;cursor:not-allowed}
	.tenant-selector{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:#132031;border:1px solid #36485b;padding:14px 16px;margin-bottom:17px;border-radius:8px}
	.tenant-selector label,.tenant-selector span{font-size:10px;color:#9aabc0;font-weight:800;letter-spacing:.07em}
	.tenant-selector span{margin-left:auto}
	select,input,textarea{width:100%;min-width:0;border:1px solid #37495e;border-radius:6px;padding:11px 12px;background:#0a141f;color:#edf2f9;font-size:12px}
	.tenant-selector select{width:auto;min-width:190px;max-width:100%}
	.workspace{display:grid;grid-template-columns:minmax(260px,.73fr) minmax(470px,1.6fr);gap:15px;align-items:start;margin-bottom:16px}
	.workspace.bottom{grid-template-columns:repeat(2,minmax(0,1fr))}
	.panel{background:#111b29;border:1px solid #2e4052;border-radius:10px;min-width:0;overflow:hidden}
	.section-head{padding:20px;border-bottom:1px solid #293a4b}
	.section-head h3{font-size:18px;margin:9px 0 0}.section-head p{font-size:12px;color:#92a6bb;line-height:1.7}
	.rule-items{max-height:720px;overflow-y:auto}.rule-items button,.findings button{background:transparent;border:0;border-top:1px solid #2b3c4e;color:#f2f6fa;display:block;text-align:left;width:100%;cursor:pointer;padding:17px}
	.rule-items button.chosen,.findings button.chosen{background:#332430;box-shadow:inset 3px 0 #e14a63}
	.rule-items button:hover,.findings button:hover{background:#203148}
	.rule-items strong{display:block;font-size:12px;line-height:1.6;margin:9px 0}
	.rule-items small,.findings small{font-size:10px;color:#92a9bf}
	.line{display:flex;justify-content:space-between;align-items:center;gap:10px}
	.meta{font-size:11px;color:#9aadbf}
	.rule-overview{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;padding:19px}
	.rule-overview>div{display:flex;flex-direction:column;gap:10px;background:#0b1623;padding:12px;border:1px solid #2b3c50;border-radius:6px}
	.rule-overview span{font-size:9px;color:#91a6bb;font-weight:800;letter-spacing:.05em}.rule-overview strong{font-size:11px;text-transform:capitalize;overflow-wrap:anywhere}
	.inner{border-top:1px solid #2c3b50;padding:19px}.inner h4{font-size:16px;margin:9px 0 18px}
	.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px;margin-bottom:15px}
	.form-grid label,.input-label{color:#a9bbcc;display:flex;flex-direction:column;gap:7px;font-size:11px;font-weight:750}
	.form-grid label.wide{grid-column:1/-1}.form-grid input,.form-grid select,.form-grid textarea{font-weight:400}
	.muted{color:#99adc0;font-size:11px;line-height:1.7;margin:14px 0}
	.creation{padding:18px;margin-bottom:16px}.creation .section-head{padding:0 0 16px;margin-bottom:15px}
	.journal-entry{border-top:1px solid #2c4050;margin-top:12px;padding-top:12px;font-size:11px}
	.journal-entry strong{font-size:11px}.journal-entry p{color:#aebdcb;line-height:1.65;margin:7px 0}
	.journal-entry small{color:#849caf}
	.records,.findings{max-height:500px;overflow-y:auto}.record{border-top:1px solid #2c4050;padding:16px}
	.record strong{font-size:12px}.record span{font-size:10px;color:#95aabf;font-weight:800;text-transform:uppercase}
	.record span.positive{color:#ef9bb0}.record p,.record small{font-size:11px;color:#a2b4c8;line-height:1.6}
	.findings strong{font-size:12px}.findings span{font-size:10px;color:#e8b8ac}
	.findings small{display:block;margin-top:10px;line-height:1.7}
	.empty{font-size:12px;padding:24px;color:#a8b8ca;background:#182434;border:1px solid #354354;border-radius:8px;line-height:1.7}
	.empty strong{font-size:14px;color:#eef4fa}.empty p{font-size:12px}
	.feedback{padding:14px;border:1px solid #437467;border-radius:7px;background:#1d3030;color:#b7dccd;font-size:12px;margin:15px 0}
	.feedback.error{border-color:#875367;background:#32232f;color:#f2bac5}
	.detections footer{display:flex;justify-content:space-between;gap:13px;margin-top:24px;padding-top:18px;border-top:1px solid #304051;font-size:10px;font-weight:800;color:#7891a9;letter-spacing:.06em}
	@media(max-width:1130px){.workspace,.workspace.bottom{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
	@media(max-width:730px){.heading,.lab-banner{flex-direction:column;align-items:flex-start}.status{margin-left:0}.rule-overview{grid-template-columns:repeat(2,minmax(0,1fr))}.detections footer{flex-direction:column}}
	@media(max-width:530px){.metrics,.form-grid{grid-template-columns:1fr}.form-grid label.wide{grid-column:1}.tenant-selector select{width:100%}}
</style>
