<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { visibleLabTenants } from '$lib/sentry-lab/scope';
	import type { LabIdentity, LabMembership, LabTenant } from '$lib/sentry-lab/scope';

	/** Isolated RH Sentry training-lab events. This never connects to Wazuh. */
	export let labSessionUser: string;
	export let csrf: string;
	export let onOpenApiLab: () => void;
	export let onOpenCase: (tenantId: string, caseId: string) => void;

	type Scenario = { id: string; name: string; description: string };
	type EventRecord = {
		id: number; batchId: number; eventType: string; occurredAt: string;
		source: string; actor: string; host: string; description: string;
		attributes: Record<string, string | number | boolean>;
	};
	type CorrelationRecord = {
		id: number; batchId: number; ruleId: string; title: string;
		explanation: string; caseId: string | null;
		eventIds: number[]; createdAt: string;
	};
	const API = 'http://127.0.0.1:8001';
	let user = '';
	let members: LabMembership[] = [];
	let tenants: LabTenant[] = [];
	let selectedTenant = '';
	let scenarios: Scenario[] = [];
	let selectedScenario = 'impossible-travel';
	let events: EventRecord[] = [];
	let matches: CorrelationRecord[] = [];
	let busy = false;
	let loading = false;
	let online = false;
	let message = '';
	let pendingKey = '';
	let requestGeneration = 0;
	let destroyed = false;

	$: canSubmit = Boolean(user && labSessionUser === user && csrf);
	$: selectedScenarioDetails = scenarios.find((item) => item.id === selectedScenario) ?? null;

	async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
		const res = await fetch(API + path, {
			...init, credentials: 'include', cache: 'no-store',
			headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) }
		});
		if (!res.ok) {
			let detail = 'HTTP ' + res.status;
			try {
				const value = await res.json();
				if (typeof value.detail === 'string') detail += ': ' + value.detail;
			} catch { /* Keep generic error. */ }
			throw new Error(detail);
		}
		return (await res.json()) as T;
	}

	function scopePath(suffix: string): string {
		return '/api/tenants/' + encodeURIComponent(selectedTenant) + '/lab/' + suffix;
	}

	async function loadData() {
		const generation = ++requestGeneration;
		events = [];
		matches = [];
		scenarios = [];
		pendingKey = '';
		message = '';
		if (!selectedTenant) return;
		try {
			const [options, eventPage, correlationPage] = await Promise.all([
				request<{ tenantId: string; items: Scenario[] }>(scopePath('scenarios')),
				request<{ tenantId: string; items: EventRecord[] }>(scopePath('events')),
				request<{ tenantId: string; items: CorrelationRecord[] }>(scopePath('correlations'))
			]);
			if (destroyed || generation !== requestGeneration) return;
			if ([options.tenantId, eventPage.tenantId, correlationPage.tenantId]
				.some((scope) => scope !== selectedTenant)) {
				throw new Error('Unexpected tenant in API response; synthetic results withheld.');
			}
			scenarios = options.items;
			events = eventPage.items;
			matches = correlationPage.items;
			if (!scenarios.some((item) => item.id === selectedScenario)) {
				selectedScenario = scenarios[0]?.id ?? '';
			}
		} catch (error) {
			if (destroyed || generation !== requestGeneration) return;
			events = []; matches = []; scenarios = [];
			message = error instanceof Error ? error.message : 'Local synthetic events are unavailable.';
		}
	}

	async function initialize() {
		loading = true;
		online = false;
		user = '';
		tenants = [];
		members = [];
		selectedTenant = '';
		scenarios = [];
		events = [];
		matches = [];
		message = '';
		++requestGeneration;
		try {
			const health = await request<{ service: string; mode: string; liveSensors: number }>('/api/health');
			if (health.service !== 'rh-sentry-lab' || health.mode !== 'synthetic-local-only' || health.liveSensors !== 0) {
				throw new Error('The connected service was not the RH Sentry synthetic API lab.');
			}
			online = true;
			const me = await request<LabIdentity>('/api/me');
			const organisationList = await request<{ items: LabTenant[] }>('/api/tenants');
			if (destroyed) return;
			user = me.user;
			members = me.memberships.filter((item) =>
				item.role === 'soc_analyst' || item.role === 'soc_lead'
			);
			tenants = visibleLabTenants(organisationList.items, members);
			selectedTenant = tenants[0]?.id ?? '';
			if (selectedTenant) await loadData();
			else message = 'An active fictional SOC analyst membership is required to view or submit synthetic event batches.';
		} catch (error) {
			if (destroyed) return;
			message = error instanceof Error ? error.message : 'The local API is unavailable.';
			user = ''; tenants = []; events = []; matches = [];
		} finally {
			if (!destroyed) loading = false;
		}
	}

	async function ingestScenario() {
		if (!canSubmit || !selectedTenant || !selectedScenario || busy) return;
		busy = true;
		message = '';
		// A generated identifier retries safely; the backend deduplicates per tenant.
		if (!pendingKey) pendingKey = 'lab-' + crypto.randomUUID().replaceAll('-', '');
		try {
			const response = await request<{
				batchId: number; scenarioId: string; replayed: boolean;
				eventCount?: number; correlationCount?: number;
			}>(scopePath('scenarios/ingest'), {
				method: 'POST',
				headers: { 'X-CSRF-Token': csrf },
				body: JSON.stringify({ scenarioId: selectedScenario, idempotencyKey: pendingKey })
			});
			message = response.replayed
				? 'Previously submitted synthetic batch #' + response.batchId + ' was safely reused.'
				: 'Stored synthetic batch #' + response.batchId + ' (' + response.eventCount
					+ ' events, ' + response.correlationCount + ' illustrative correlations).';
			pendingKey = '';
			// Refresh without changing the current authenticated tenant.
			const [eventPage, correlationPage] = await Promise.all([
				request<{ tenantId: string; items: EventRecord[] }>(scopePath('events')),
				request<{ tenantId: string; items: CorrelationRecord[] }>(scopePath('correlations'))
			]);
			if (eventPage.tenantId === selectedTenant && correlationPage.tenantId === selectedTenant) {
				events = eventPage.items;
				matches = correlationPage.items;
			}
		} catch (error) {
			message = error instanceof Error ? error.message : 'Synthetic scenario could not be saved.';
			// Leave pendingKey unchanged so a retry cannot produce duplicates.
		} finally {
			busy = false;
		}
	}

	function chooseScenario(id: string) {
		selectedScenario = id;
		pendingKey = '';
	}

	onMount(() => { void initialize(); });
	onDestroy(() => { destroyed = true; ++requestGeneration; });
</script>

<div class="pipeline">
	<div class="notice">
		<div class="symbol" aria-hidden="true">◈</div>
		<div><strong>Synthetic ingestion & correlation laboratory</strong>
			<p>Generate predefined fictional events, store their provenance in local SQLite and inspect deterministic example correlations. No external event source, SIEM, endpoint collector or AI model is connected.</p>
		</div>
		<span>NO LIVE INGESTION</span>
	</div>

	<div class="metric-grid">
		<div><span>LIVE CONNECTED SENSORS</span><strong>00</strong><small>Development lab only</small></div>
		<div><span>STORED SAMPLE EVENTS</span><strong>{events.length.toString().padStart(2,'0')}</strong><small>Latest 100 from tenant</small></div>
		<div><span>SAMPLE CORRELATIONS</span><strong>{matches.length.toString().padStart(2,'0')}</strong><small>Illustrative rule matches</small></div>
		<div><span>CURRENT DATA SOURCE</span><strong class="small-value">SQLite</strong><small>Fictional tenant-scoped records</small></div>
	</div>

	<div class="toolbar">
		<div><span class="eyebrow">DETECTION OPERATIONS / LOCAL LAB</span><h2>Event processing workbench</h2>
			<p>Account: {user || 'Unauthenticated'} · Connection: {online ? 'localhost API available' : 'offline'}</p></div>
		<div class="toolbar-actions">
			<button type="button" class="secondary" disabled={loading || busy} on:click={() => void initialize()}>Refresh lab ↻</button>
			<button type="button" class="secondary" on:click={onOpenApiLab}>Open API Lab ↗</button>
		</div>
	</div>

	{#if loading}
		<div class="empty">Checking lab identity and event permissions...</div>
	{:else if !online || !user || !selectedTenant}
		<div class="empty"><strong>Local analyst access required</strong><p>{message || 'Start the local Python backend and sign in as an authorised synthetic SOC analyst through API Lab.'}</p><button class="primary" type="button" on:click={onOpenApiLab}>Open API Lab ↗</button></div>
	{:else}
		<div class="workbench">
			<section class="panel">
				<div class="panel-head"><span class="eyebrow">EVENT GENERATOR / FICTITIOUS INPUT</span><h3>Scenario library</h3></div>
				<div class="field">
					<label for="pipeline-tenant">AUTHORISED DEMONSTRATION ORGANISATION</label>
					<select id="pipeline-tenant" bind:value={selectedTenant} disabled={busy} on:change={() => void loadData()}>
						{#each tenants as tenant (tenant.id)}<option value={tenant.id}>{tenant.name}</option>{/each}
					</select>
				</div>
				<div class="scenarios">
					{#each scenarios as scenario (scenario.id)}
						<button type="button" class:chosen={selectedScenario===scenario.id} aria-pressed={selectedScenario===scenario.id} disabled={busy} on:click={() => chooseScenario(scenario.id)}>
							<strong>{scenario.name}</strong>
							<small>{scenario.description}</small>
						</button>
					{:else}<p class="empty">No synthetic scenarios available for this account.</p>{/each}
				</div>
				<div class="action">
					<span class="eyebrow">SELECTED TEST</span>
					<strong>{selectedScenarioDetails?.name ?? 'Choose a scenario'}</strong>
					<p>The backend generates predetermined sample fields. This form cannot upload logs, request a URL or run a network command.</p>
					<button type="button" class="primary" disabled={!canSubmit || !selectedScenario || busy} on:click={ingestScenario}>{busy ? 'Storing synthetic events...' : 'Generate & correlate sample batch ↗'}</button>
					{#if !canSubmit}<small>Sign in again via API Lab to receive a session-bound CSRF token for writes.</small>{/if}
				</div>
			</section>
			<section class="panel">
				<div class="panel-head"><span class="eyebrow">RULE OUTPUT / DEMONSTRATION ONLY</span><h3>Correlation results</h3></div>
				<div class="correlations">
					{#each matches as match (match.id)}
						<article class="correlation">
							<div class="correlation-top"><span>{match.ruleId}</span><span>EXAMPLE MATCH</span></div>
							<strong>{match.title}</strong>
							<p>{match.explanation}</p>
							<div class="corr-meta">Batch #{match.batchId} · Event IDs {match.eventIds.join(', ')} · {match.createdAt}</div>
							{#if match.caseId}
								<button type="button" class="link-button" on:click={() => onOpenCase(selectedTenant, match.caseId ?? '')}>Open existing fictional case {match.caseId} ↗</button>
							{:else}
								<div class="unlinked">No case is linked for this fictional tenant. No incident was created.</div>
							{/if}
						</article>
					{:else}
						<div class="empty">No correlation matches for this authorised tenant. Try the impossible-travel or encoded-PowerShell synthetic scenarios.</div>
					{/each}
				</div>
			</section>
		</div>

		<section class="panel event-panel">
			<div class="panel-head"><div><span class="eyebrow">EVENT PROVENANCE / STORED IN SQLITE</span><h3>Synthetic event stream</h3></div><span class="counter">MOST RECENT {events.length}</span></div>
			<div class="event-list">
				{#each events as entry (entry.id)}
					<div class="event">
						<div class="event-top"><strong>#{entry.id} · {entry.eventType.replaceAll('_',' ')}</strong><span>{entry.occurredAt}</span></div>
						<p>{entry.description}</p>
						<div class="event-meta">Source: {entry.source} · Host: {entry.host} · Batch #{entry.batchId}</div>
						<details><summary>Inspect synthetic fields</summary><pre>{JSON.stringify(entry.attributes,null,2)}</pre></details>
					</div>
				{:else}<div class="empty">No events in this synthetic tenant. Select a scenario above to generate a test batch.</div>{/each}
			</div>
		</section>
	{/if}

	{#if message}<div class="feedback" role="status">{message}</div>{/if}
	<footer>RH SENTRY / LOCAL DEVELOPMENT PIPELINE <span>0 LIVE EVENTS · NO AUTOMATED RESPONSE · NO REAL CUSTOMER DATA</span></footer>
</div>

<style>
	.pipeline{color:#eaf1f8}
	.notice{display:flex;gap:16px;align-items:center;padding:19px;background:linear-gradient(110deg,#29252e,#151e2a);border:1px solid #684959;border-radius:10px;margin-bottom:16px}
	.symbol{border:1px solid #855060;border-radius:8px;color:#f098aa;display:grid;place-items:center;width:44px;height:44px;font-size:25px;flex-shrink:0}
	.notice strong{font-size:14px}.notice p{color:#acbac8;font-size:12px;line-height:1.7;margin:7px 0 0}
	.notice>span{border:1px solid #8b6748;color:#ecc398;font-size:10px;font-weight:800;border-radius:5px;padding:10px;white-space:nowrap;margin-left:auto}
	.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
	.metric-grid>div{display:flex;flex-direction:column;gap:8px;border:1px solid #2a3949;background:#111a25;padding:18px;border-radius:9px}
	.metric-grid span{font-size:10px;letter-spacing:.07em;font-weight:750;color:#90a3b8}.metric-grid strong{font-size:29px}.metric-grid strong.small-value{font-size:22px}.metric-grid small{font-size:11px;color:#7e92a7}
	.toolbar{display:flex;justify-content:space-between;align-items:center;gap:15px;margin:25px 0 19px}
	.eyebrow{font-size:10px;color:#e56d7d;letter-spacing:.12em;font-weight:800}
	.toolbar h2{font-size:22px;margin:9px 0}.toolbar p{font-size:12px;color:#94a6bb;margin:0}
	.toolbar-actions{display:flex;gap:8px;flex-wrap:wrap}
	.primary,.secondary,.link-button{padding:11px 14px;border-radius:6px;font-size:11px;font-weight:800;border:1px solid #7a4d5c;cursor:pointer;background:#392533;color:#f6bfca}
	.primary{background:#de3651;color:#fff;border-color:#f04b65}
	.primary:disabled,.secondary:disabled{opacity:.4;cursor:not-allowed}
	.workbench{display:grid;grid-template-columns:minmax(280px,.83fr) minmax(380px,1.3fr);gap:15px;align-items:start}
	.panel{border:1px solid #2b384a;border-radius:9px;background:#111a26;overflow:hidden;min-width:0}
	.panel-head{padding:22px;display:flex;justify-content:space-between;align-items:start;gap:14px}
	.panel h3{font-size:18px;margin:10px 0 0}
	.field{padding:0 20px 16px;display:flex;flex-direction:column;gap:9px}
	.field label{font-size:10px;color:#9fb0c3;letter-spacing:.07em;font-weight:800}
	.field select{background:#0a121e;color:#e0eaf5;border:1px solid #38495a;border-radius:6px;padding:12px;font-size:12px;width:100%}
	.field select option{background:#151c29}
	.scenarios{padding:0 15px}
	.scenarios button{display:block;width:100%;text-align:left;padding:17px;margin-bottom:9px;border:1px solid #324254;border-radius:7px;background:#0b1420;color:#e6eff7;cursor:pointer}
	.scenarios button.chosen{background:#352330;border-color:#b14d62}
	.scenarios strong{font-size:13px;display:block}.scenarios small{font-size:11px;line-height:1.7;color:#9caebe;display:block;margin-top:7px}
	.action{padding:20px;border-top:1px solid #354154;margin-top:13px;display:flex;flex-direction:column;align-items:start;gap:12px}
	.action strong{font-size:13px}.action p{font-size:12px;color:#9dabbc;line-height:1.7;margin:0}.action small{font-size:11px;color:#d6b29c}
	.correlations{max-height:660px;overflow-y:auto;padding:0 17px 15px}
	.correlation{border:1px solid #394458;background:#172232;padding:19px;border-radius:8px;margin-bottom:12px}
	.correlation-top{display:flex;justify-content:space-between;gap:10px;color:#e2a2b0;font-size:10px;font-weight:800;letter-spacing:.05em;margin-bottom:13px}
	.correlation>strong{font-size:14px}.correlation p{font-size:12px;color:#b6c3d1;line-height:1.75}
	.corr-meta{font-size:10px;color:#8498ad;margin:13px 0}
	.link-button{background:#372634;color:#f5c5ce;margin-top:6px}
	.unlinked{font-size:11px;color:#bda897;margin-top:15px}
	.event-panel{margin-top:15px}
	.counter{color:#8ca1b5;font-size:10px}
	.event-list{padding:0 20px 20px;display:grid;gap:11px;max-height:630px;overflow-y:auto}
	.event{border:1px solid #314153;border-radius:8px;background:#0b1521;padding:17px}
	.event-top{display:flex;justify-content:space-between;gap:10px;font-size:12px}
	.event-top strong{text-transform:capitalize}.event-top span{font-size:10px;color:#9bacc1}
	.event p{font-size:12px;line-height:1.7;color:#b6c4d2}.event-meta{font-size:11px;color:#8c9fb3;margin-top:12px}
	.event details{margin-top:13px;font-size:11px;color:#c5d3e1;cursor:pointer}
	.event pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#a9d3e9;font-size:11px;line-height:1.7;padding:12px;background:#08111a;border-radius:5px}
	.empty{padding:25px;color:#a6b4c5;font-size:12px;line-height:1.7;background:#131e2b;border-radius:7px}
	.empty strong{color:#edf2f8}.empty p{font-size:12px}.empty button{margin-top:9px}
	.feedback{padding:14px 17px;margin-top:16px;border:1px solid #624b4d;border-radius:8px;background:#29232c;color:#e8c2af;font-size:12px;line-height:1.7}
	.pipeline footer{display:flex;justify-content:space-between;gap:12px;padding-top:18px;margin-top:25px;border-top:1px solid #293746;font-size:10px;font-weight:800;color:#74889c;letter-spacing:.06em}
	@media(max-width:1120px){.workbench{grid-template-columns:1fr}.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
	@media(max-width:750px){.notice,.toolbar{flex-direction:column;align-items:flex-start}.notice>span{margin-left:0}.pipeline footer{flex-direction:column}}
	@media(max-width:530px){.metric-grid{grid-template-columns:1fr}.event-top{flex-direction:column}}
</style>
