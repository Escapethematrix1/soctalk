<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { chooseLabTenant, visibleLabTenants } from '$lib/sentry-lab/scope';
	import type { LabCase, LabIdentity, LabTenant } from '$lib/sentry-lab/scope';

	// Read-only fictional dashboard. All counts come from backend queries and
	// cannot be mixed with the separate static demonstration counters.
	export let selectedTenantId: string;
	export let onOpenApiLab: () => void;
	export let onOpenCase: (tenantId: string, incidentId: string) => void;
	export let onOpenPipeline: () => void;

	type Summary = {
		tenantId: string;
		tenantName: string;
		source: 'local-sqlite-fictional';
		liveTelemetry: false;
		liveSensors: number;
		liveCoveragePercent: number;
		aiAnalysisConnected: false;
		incidentSummary: {
			total: number;
			open: number;
			critical: number;
			high: number;
			assigned: number;
			byStatus: Record<string, number>;
		};
		assetSummary: {registered:number; active:number; maintenance:number; retired:number; connected:number};
		syntheticEventCount: number | null;
		syntheticCorrelationCount: number | null;
		recentIncidents: LabCase[];
	};

	const BASE = 'http://127.0.0.1:8001';
	let identity = '';
	let tenants: LabTenant[] = [];
	let summary: Summary | null = null;
	let online = false;
	let loading = false;
	let fetching = false;
	let error = '';
	let destroyed = false;
	let requestId = 0;

	$: statuses = summary ? Object.entries(summary.incidentSummary.byStatus) : [];
	$: totalStatusCount = statuses.reduce((sum, [, count]) => sum + count, 0);

	async function get<T>(path: string): Promise<T> {
		const response = await fetch(BASE + path, {
			credentials: 'include',
			cache: 'no-store',
			headers: { Accept: 'application/json' }
		});
		if (!response.ok) {
			let detail = 'HTTP ' + response.status;
			try {
				const payload = await response.json();
				if (typeof payload.detail === 'string') detail += ': ' + payload.detail;
			} catch {
				// Preserve the generic HTTP status for non-JSON errors.
			}
			throw new Error(detail);
		}
		return (await response.json()) as T;
	}

	function resetAccess() {
		summary = null;
		identity = '';
		tenants = [];
		selectedTenantId = '';
	}

	async function fetchSummary() {
		const serial = ++requestId;
		const scope = selectedTenantId;
		summary = null; // Hide old tenant's counts during every tenant switch.
		error = '';
		fetching = Boolean(scope);
		if (!scope) {
			fetching = false;
			return;
		}
		try {
			const result = await get<Summary>(
				'/api/tenants/' + encodeURIComponent(scope) + '/lab/overview'
			);
			if (destroyed || serial !== requestId || scope !== selectedTenantId) return;
			if (result.tenantId !== scope || result.source !== 'local-sqlite-fictional' ||
				result.liveTelemetry !== false || result.liveSensors !== 0 ||
				result.aiAnalysisConnected !== false || result.assetSummary.connected !== 0 ||
				result.recentIncidents.some((item) => item.tenantId !== scope)) {
				throw new Error('Unexpected local API response; dashboard metrics withheld.');
			}
			summary = result;
		} catch (err) {
			if (destroyed || serial !== requestId) return;
			summary = null;
			error = err instanceof Error ? err.message : 'Could not load permitted dashboard data.';
		} finally {
			if (!destroyed && serial === requestId) fetching = false;
		}
	}

	async function connect() {
		const serial = ++requestId;
		const previousTenant = selectedTenantId;
		loading = true;
		online = false;
		resetAccess();
		error = '';
		try {
			const health = await get<{ service: string; mode: string; liveSensors: number }>('/api/health');
			if (health.service !== 'rh-sentry-lab' || health.mode !== 'synthetic-local-only' ||
				health.liveSensors !== 0) {
				throw new Error('Service is not the isolated RH Sentry training API.');
			}
			online = true;
			const me = await get<LabIdentity>('/api/me');
			const tenantList = await get<{ items: LabTenant[] }>('/api/tenants');
			if (destroyed || serial !== requestId) return;
			identity = me.user;
			tenants = visibleLabTenants(tenantList.items, me.memberships);
			selectedTenantId = chooseLabTenant(tenants, previousTenant);
			if (selectedTenantId) await fetchSummary();
			else error = 'This account has no customer incident membership.';
		} catch (err) {
			if (destroyed || serial !== requestId) return;
			resetAccess();
			error = err instanceof Error ? err.message : 'Local API is unavailable.';
		} finally {
			if (!destroyed) loading = false;
		}
	}

	function changeTenant() {
		void fetchSummary();
	}

	onMount(() => { void connect(); });
	onDestroy(() => { destroyed = true; ++requestId; });
</script>

<div class="local-centre">
	<div class="environment-notice">
		<div class="notice-mark" aria-hidden="true">◎</div>
		<div>
			<strong>Persistent Command Centre · local API</strong>
			<p>Counts below are calculated from authorised fictional SQLite records. They are not a live security posture assessment or AI-generated findings.</p>
		</div>
		<span class:connected={online} class="connection">{online ? 'LOCAL API ONLINE' : 'LOCAL API OFFLINE'}</span>
	</div>

	<div class="topbar">
		<div>
			<span class="kicker">RED HORIZON / TENANT-SCOPED INTELLIGENCE</span>
			<h2>Customer security overview</h2>
			<p>{identity ? 'Signed in as ' + identity : 'No authorised lab session'} · No live monitoring connected</p>
		</div>
		<div class="actions">
			<button type="button" class="secondary" on:click={() => void connect()} disabled={loading}>Refresh from SQLite ↻</button>
			<button type="button" class="secondary" on:click={onOpenApiLab}>API Lab ↗</button>
		</div>
	</div>

	{#if loading}
		<div class="empty">Verifying your local session and available customer organisations...</div>
	{:else if !identity || !online || !tenants.length}
		<div class="empty">
			<strong>Authenticated local API required</strong>
			<p>Start your Python API at 127.0.0.1:8001 and sign in through API Lab. If an account has no customer membership, the dashboard will not display another customer's information.</p>
			<button class="primary" type="button" on:click={onOpenApiLab}>Open API Lab</button>
		</div>
	{:else}
		<div class="tenant-bar">
			<label for="centre-tenant">AUTHORISED FICTIONAL ORGANISATION</label>
			<select id="centre-tenant" bind:value={selectedTenantId} on:change={changeTenant} disabled={fetching}>
				{#each tenants as tenant (tenant.id)}
					<option value={tenant.id}>{tenant.name}</option>
				{/each}
			</select>
			<span>{summary ? 'SOURCE: LOCAL SQLITE / FICTIONAL' : 'AWAITING TENANT QUERY'}</span>
		</div>
		{#if fetching}
			<div class="empty">Retrieving this organisation's persisted dashboard metrics...</div>
		{:else if summary}
			<div class="stats">
				<div><span>OPEN INVESTIGATIONS</span><strong>{summary.incidentSummary.open.toString().padStart(2, '0')}</strong><small>{summary.incidentSummary.total} total sample records</small></div>
				<div><span>OPEN CRITICAL CASES</span><strong class="red">{summary.incidentSummary.critical.toString().padStart(2, '0')}</strong><small>SQLite severity and status</small></div>
				<div><span>OPEN HIGH-SEVERITY CASES</span><strong>{summary.incidentSummary.high.toString().padStart(2, '0')}</strong><small>Persisted fictional cases</small></div>
				<div><span>REGISTERED ASSETS</span><strong>{summary.assetSummary.registered.toString().padStart(2, '0')}</strong><small>{summary.assetSummary.active} active · 0 monitored</small></div>
			</div>
			<div class="data-row">
				<div class="data-panel">
					<div class="panel-title"><span class="kicker">INCIDENT OPERATIONS</span><h3>Case state breakdown</h3></div>
					<p class="panel-caption">Calculated from {summary.incidentSummary.total} records for {summary.tenantName}. Closed cases are included in these status totals.</p>
					{#each statuses as [state, count] (state)}
						<div class="status-row">
							<div><strong>{state}</strong><span>{count} case{count === 1 ? '' : 's'}</span></div>
							<div class="bar"><span style:width={(totalStatusCount ? count / totalStatusCount * 100 : 0) + '%'}></span></div>
						</div>
					{:else}
						<div class="empty-inline">No fictional incident records in this organisation.</div>
					{/each}
					<div class="assigned">{summary.incidentSummary.assigned} non-closed cases currently assigned to an analyst.</div>
				</div>
				<div class="data-panel">
					<div class="panel-title"><span class="kicker">DETECTION DATA / TRANSPARENT COVERAGE</span><h3>Event and monitoring status</h3></div>
					<div class="source-status">
						<div><span>Stored synthetic events</span><strong>{summary.syntheticEventCount === null ? 'Restricted' : summary.syntheticEventCount}</strong></div>
						<div><span>Example correlations</span><strong>{summary.syntheticCorrelationCount === null ? 'Restricted' : summary.syntheticCorrelationCount}</strong></div>
						<div><span>Registered fictional assets</span><strong>{summary.assetSummary.registered}</strong></div>
						<div><span>Live agents</span><strong>{summary.assetSummary.connected}</strong></div>
						<div><span>AI investigation engine</span><strong>Not connected</strong></div>
						<div><span>Live coverage</span><strong>0%</strong></div>
					</div>
					<p class="panel-caption">{summary.syntheticEventCount === null
						? 'Internal synthetic event totals are restricted to authorised SOC analysts.'
						: 'Event and correlation totals come from the isolated training pipeline, not from production collectors.'}</p>
					<button type="button" class="secondary" on:click={onOpenPipeline}>Explore synthetic events ↗</button>
				</div>
			</div>
			<div class="data-panel case-panel">
				<div class="panel-title"><span class="kicker">RECENT AUTHORISED CASES</span><h3>Investigations</h3></div>
				<div class="case-list">
					{#each summary.recentIncidents as incident (incident.id)}
						<button type="button" on:click={() => onOpenCase(selectedTenantId, incident.id)}>
							<span class="case-severity" class:critical={incident.severity === 'critical'}>{incident.severity}</span>
							<span class="case-copy"><strong>{incident.title}</strong><small>{incident.id} · {incident.status} · v{incident.version} · {incident.assignedTo ?? 'Unassigned'}</small></span>
							<span class="case-arrow" aria-hidden="true">›</span>
						</button>
					{:else}
						<div class="empty-inline">No fictional cases are available for this organisation.</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
	{#if error}<p class="error" role="status">{error}</p>{/if}
	<footer>RH SENTRY · AUTHORISED LOCAL SQL VIEW <span>NO LIVE TELEMETRY · NO AUTOMATED RESPONSE · NOT FOR CUSTOMERS</span></footer>
</div>

<style>
	.local-centre {color:#eaf0f8}
	.environment-notice {display:flex;gap:16px;align-items:center;background:linear-gradient(110deg,#29232d,#151d29);border:1px solid #68505a;border-radius:9px;padding:19px;margin-bottom:19px}
	.notice-mark {display:grid;place-items:center;flex-shrink:0;width:43px;height:43px;border:1px solid #925268;border-radius:8px;color:#f4a7b6;font-size:24px}
	.environment-notice strong {font-size:15px}.environment-notice p {font-size:12px;color:#aab8c8;line-height:1.7;margin:5px 0 0}
	.connection {white-space:nowrap;margin-left:auto;font-size:10px;font-weight:800;color:#f1be97;border:1px solid #866247;padding:9px;border-radius:5px}
	.connection.connected {color:#91dbbd;border-color:#46846b}
	.topbar {display:flex;align-items:center;justify-content:space-between;gap:16px;margin:25px 0}
	.topbar h2 {font-size:23px;margin:8px 0}.topbar p {font-size:12px;color:#96a8bc;margin:0}
	.kicker {font-size:10px;letter-spacing:.12em;color:#e56a7d;font-weight:800}
	.actions {display:flex;gap:9px;flex-wrap:wrap}
	.secondary,.primary {cursor:pointer;padding:11px 13px;border:1px solid #704e5c;border-radius:6px;background:#362634;color:#f4c2cc;font-size:11px;font-weight:800}
	.primary {background:#df3753;color:#fff;border-color:#f0566d}
	.secondary:disabled {opacity:.4;cursor:not-allowed}
	.tenant-bar {display:flex;align-items:center;gap:13px;flex-wrap:wrap;border:1px solid #344254;border-radius:8px;padding:14px 18px;margin-bottom:16px;background:#131d2a}
	.tenant-bar label {color:#a6b9ce;font-size:10px;font-weight:800;letter-spacing:.06em}
	.tenant-bar select {min-width:190px;max-width:100%;border:1px solid #465467;background:#0a131f;padding:10px;border-radius:6px;color:#e3ebf4;font-size:12px}
	.tenant-bar option {background:#111b28}.tenant-bar>span {color:#8c9eb3;font-size:10px;margin-left:auto}
	.stats {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px}
	.stats>div {background:#111a26;border:1px solid #2c3a4b;border-radius:8px;padding:18px;display:flex;flex-direction:column;gap:10px}
	.stats span {font-size:10px;letter-spacing:.06em;font-weight:800;color:#95a8bf}.stats strong {font-size:29px;color:#eaf1f9}
	.stats strong.red {color:#f06d84}.stats small {font-size:11px;color:#90a0b4;line-height:1.5}
	.data-row {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px;margin-bottom:15px}
	.data-panel {background:#111a26;border:1px solid #2b3b4d;border-radius:9px;min-width:0;padding:22px}
	.panel-title h3 {font-size:18px;margin:8px 0 0}.panel-caption {font-size:12px;color:#9eb0c3;line-height:1.7;margin:15px 0 20px}
	.status-row {margin:18px 0}.status-row>div:first-child {display:flex;justify-content:space-between;gap:9px;text-transform:capitalize;font-size:12px}
	.status-row span {color:#9fb0c2}.status-row strong {font-size:12px}
	.bar {margin-top:10px;width:100%;height:9px;border-radius:7px;background:#283447;overflow:hidden}
	.bar span {display:block;height:100%;border-radius:7px;background:#dc465f}
	.assigned {border-top:1px solid #314153;padding-top:15px;margin-top:20px;color:#aebdca;font-size:11px;line-height:1.7}
	.source-status {margin-top:16px}.source-status>div {display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid #29394d;padding:12px 0;font-size:12px}
	.source-status span {color:#9bacc1}.source-status strong {font-size:12px}
	.case-panel {padding-bottom:8px}.case-list {margin-top:17px}
	.case-list button {width:100%;display:flex;align-items:center;gap:14px;cursor:pointer;text-align:left;border:0;border-top:1px solid #2b3949;background:transparent;color:#eaf0f8;padding:17px 2px}
	.case-list button:hover {background:#1c2939}.case-severity {color:#f3ca94;text-transform:uppercase;font-size:10px;font-weight:800;min-width:53px}
	.case-severity.critical {color:#ef7287}.case-copy {display:flex;flex-direction:column;gap:7px;min-width:0;flex:1}
	.case-copy strong {font-size:13px}.case-copy small {color:#91a3b7;font-size:11px;line-height:1.6}.case-arrow {color:#f07889;font-size:22px}
	.empty,.empty-inline {padding:24px;color:#acbacb;font-size:12px;line-height:1.7;background:#182434;border:1px solid #334253;border-radius:8px}
	.empty strong {display:block;font-size:14px;color:#eff3f8}.empty p {line-height:1.75}
	.empty-inline {background:transparent;border:0;padding:18px 0}
	.error {padding:14px;color:#f0bd9a;font-size:12px;background:#2d2529;border:1px solid #785648;border-radius:7px}
	.local-centre footer {display:flex;gap:12px;justify-content:space-between;border-top:1px solid #2c3b4d;padding-top:18px;margin-top:24px;color:#75899d;font-size:10px;font-weight:800;letter-spacing:.06em}
	@media(max-width:1050px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.data-row{grid-template-columns:1fr}}
	@media(max-width:700px){.topbar,.environment-notice{flex-direction:column;align-items:flex-start}.connection{margin-left:0}.local-centre footer{flex-direction:column}}
	@media(max-width:550px){.stats{grid-template-columns:1fr}}
</style>
