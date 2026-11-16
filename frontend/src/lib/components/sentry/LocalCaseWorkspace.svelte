<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import IncidentCaseLab from '$lib/components/sentry/IncidentCaseLab.svelte';
	import { chooseLabCase, chooseLabTenant, hasLabEditRole, visibleLabTenants } from '$lib/sentry-lab/scope';
	import type { LabCase, LabTenant, LabMembership, LabIdentity } from '$lib/sentry-lab/scope';

	// Never merge these server-returned cases with simulated AI/response fixtures.
	export let mode: 'incidents' | 'analyst';
	export let selectedTenantId: string;
	export let selectedCaseId: string;
	export let csrf: string;
	export let labSessionUser: string;
	export let onOpenApiLab: () => void;
	export let onSwitchWorkspace: (tenantId: string, incidentId: string) => void;

	const API = 'http://127.0.0.1:8001';
	let identityUser = '';
	let tenants: LabTenant[] = [];
	let memberships: LabMembership[] = [];
	let incidents: LabCase[] = [];
	let checked = false;
	let online = false;
	let loading = false;
	let loadingCases = false;
	let message = '';
	let search = '';
	let requestSequence = 0;
	let caseSequence = 0;
	let destroyed = false;

	$: selected = incidents.find((item) => item.id === selectedCaseId) ?? null;
	$: hasAnalystRole = hasLabEditRole(memberships, selectedTenantId);
	// UI permission is a convenience only; the Python API checks the actor.
	$: canEdit = hasAnalystRole && Boolean(csrf) && labSessionUser === identityUser;
	$: results = incidents.filter((item) =>
		[item.title, item.id, item.status, item.assignedTo ?? ''].join(' ').toLowerCase()
			.includes(search.trim().toLowerCase())
	);
	$: openCases = incidents.filter((item) => item.status !== 'closed').length;

	async function get<T>(path: string): Promise<T> {
		const response = await fetch(API + path, {
			credentials: 'include', cache: 'no-store', headers: { Accept: 'application/json' }
		});
		if (!response.ok) {
			let detail = 'HTTP ' + response.status;
			try {
				const body = await response.json();
				if (typeof body.detail === 'string') detail += ': ' + body.detail;
			} catch { /* Keep generic error on invalid JSON. */ }
			throw new Error(detail);
		}
		return (await response.json()) as T;
	}

	async function loadCases() {
		const serial = ++caseSequence;
		const tenant = selectedTenantId;
		const preferredCaseId = selectedCaseId;
		// Clear previous tenant's results before requesting another tenant.
		incidents = [];
		selectedCaseId = '';
		loadingCases = Boolean(tenant);
		message = '';
		if (!tenant) { loadingCases = false; return; }
		try {
			const response = await get<{ tenantId: string; items: LabCase[] }>(
				'/api/tenants/' + encodeURIComponent(tenant) + '/incidents'
			);
			if (destroyed || serial !== caseSequence || tenant !== selectedTenantId) return;
			if (response.tenantId !== tenant || response.items.some((item) => item.tenantId !== tenant)) {
				throw new Error('Unexpected tenant in response; records withheld.');
			}
			incidents = response.items;
			selectedCaseId = chooseLabCase(incidents, preferredCaseId);
			message = 'Loaded incident records from the authenticated, tenant-scoped local API.';
		} catch (error) {
			if (destroyed || serial !== caseSequence) return;
			incidents = [];
			selectedCaseId = '';
			message = error instanceof Error ? error.message : 'Local incident query failed.';
		} finally {
			if (!destroyed && serial === caseSequence) loadingCases = false;
		}
	}

	async function reload() {
		const serial = ++requestSequence;
		++caseSequence;
		loading = true;
		checked = false;
		online = false;
		identityUser = '';
		memberships = [];
		tenants = [];
		incidents = [];
		const previousTenant = selectedTenantId;
		const previousCase = selectedCaseId;
		selectedTenantId = '';
		selectedCaseId = '';
		message = '';
		try {
			const health = await get<{ service: string; mode: string; liveSensors: number }>('/api/health');
			if (health.service !== 'rh-sentry-lab' || health.mode !== 'synthetic-local-only' || health.liveSensors !== 0) {
				throw new Error('Service is not the isolated RH Sentry localhost lab.');
			}
			online = true;
			const me = await get<LabIdentity>('/api/me');
			const allowed = await get<{ items: LabTenant[] }>('/api/tenants');
			if (destroyed || serial !== requestSequence) return;
			identityUser = me.user;
			memberships = me.memberships;
			tenants = visibleLabTenants(allowed.items, memberships);
			selectedTenantId = chooseLabTenant(tenants, previousTenant);
			if (selectedTenantId) {
				await loadCases();
				if (selectedTenantId === previousTenant && incidents.some((item) => item.id === previousCase)) {
					selectedCaseId = previousCase;
				}
			} else {
				message = 'This identity has no tenant incident membership, even if it can list customer metadata.';
			}
		} catch (error) {
			if (destroyed || serial !== requestSequence) return;
			identityUser = '';
			memberships = [];
			tenants = [];
			incidents = [];
			selectedTenantId = '';
			selectedCaseId = '';
			message = error instanceof Error ? error.message : 'Could not connect to the localhost API.';
		} finally {
			if (!destroyed && serial === requestSequence) {
				checked = true;
				loading = false;
			}
		}
	}

	function changeTenant() {
		search = '';
		void loadCases();
	}
	function switchWorkspace() {
		if (selected && selected.tenantId === selectedTenantId) {
			onSwitchWorkspace(selectedTenantId, selected.id);
		}
	}

	onMount(() => { void reload(); });
	onDestroy(() => {
		destroyed = true;
		requestSequence += 1;
		caseSequence += 1;
	});
</script>

<div class="local-workspace">
	<div class="lab-banner">
		<div class="mark" aria-hidden="true">◎</div>
		<div><strong>{mode === 'incidents' ? 'Persistent incident workspace' : 'Analyst casework · Human review'}</strong>
			<p>{mode === 'incidents'
				? 'Authorised fictional case records from the separate Python API and SQLite database.'
				: 'Review stored cases, maintain notes and inspect history. No AI inference or automated response is connected.'}</p></div>
		<span class="lab-status" class:online>{online ? 'LOCAL API · SYNTHETIC' : 'API NOT CONNECTED'}</span>
	</div>

	<div class="stats">
		<div><span>AVAILABLE CUSTOMERS</span><strong>{tenants.length.toString().padStart(2, '0')}</strong><small>Server-issued memberships</small></div>
		<div><span>SELECTED CUSTOMER CASES</span><strong>{incidents.length.toString().padStart(2, '0')}</strong><small>SQLite records only</small></div>
		<div><span>NON-CLOSED CASES</span><strong>{openCases.toString().padStart(2, '0')}</strong><small>Fictional incident states</small></div>
		<div><span>LIVE TELEMETRY</span><strong>00</strong><small>No sensors or AI services</small></div>
	</div>

	<div class="toolbar">
		<div><span class="eyebrow">RH SENTRY / LOCAL API WORKSPACE</span>
			<h2>{mode === 'incidents' ? 'Customer-scoped incident queue' : 'Human analyst investigation queue'}</h2>
			<p>Lab identity: <strong>{identityUser || 'Not signed in'}</strong> · {hasAnalystRole ? 'Analyst membership' : 'Read-only or unauthenticated'}</p></div>
		<div class="buttons">
			<button type="button" class="secondary" on:click={() => void reload()} disabled={loading}>Refresh local session ↻</button>
			<button type="button" class="secondary" on:click={onOpenApiLab}>Open API Lab ↗</button>
		</div>
	</div>

	{#if loading}
		<div class="empty-state">Checking the localhost session and permitted organisations...</div>
	{:else if !online || !identityUser}
		<div class="empty-state"><strong>{online ? 'Lab sign-in required' : 'Local API is unavailable'}</strong>
			<p>{online ? 'Sign in from API Lab first.' : 'Start your Python backend on 127.0.0.1:8001.'}</p>
			<button type="button" class="primary" on:click={onOpenApiLab}>Open API Lab ↗</button></div>
	{:else if !tenants.length}
		<div class="empty-state">This account has no tenant incident access. A platform metadata role does not grant access to customer records.</div>
	{:else}
		<div class="queue-layout">
			<section class="panel queue">
				<div class="panel-heading"><div><span class="eyebrow">SERVER-DEFINED TENANT</span><h3>Local cases</h3></div><span class="count">{results.length} SHOWN</span></div>
				<div class="controls">
					<label for="local-customer">AUTHORISED CUSTOMER</label>
					<select id="local-customer" bind:value={selectedTenantId} on:change={changeTenant} disabled={loadingCases}>
						{#each tenants as tenant (tenant.id)}<option value={tenant.id}>{tenant.name}</option>{/each}
					</select>
					<label for="local-case-search">SEARCH RETURNED CASES</label>
					<input id="local-case-search" type="search" bind:value={search} placeholder="Search incident or analyst..."/>
				</div>
				<div class="queue-rows">
					{#each results as item (item.id)}
						<button type="button" class:chosen={selectedCaseId === item.id} aria-pressed={selectedCaseId === item.id} on:click={() => (selectedCaseId = item.id)}>
							<div class="item-top"><span>{item.id}</span><span class:critical={item.severity === 'critical'}>{item.severity}</span></div>
							<strong>{item.title}</strong>
							<div class="item-bottom"><span>{item.status}</span><span>v{item.version}</span></div>
							<small>{item.assignedTo ? 'Assigned: ' + item.assignedTo : 'Unassigned'}</small>
						</button>
					{:else}<p class="empty-row">{loadingCases ? 'Loading cases...' : 'No cases match your search.'}</p>{/each}
				</div>
				<div class="queue-foot">PERSISTENT SQLITE RECORDS · NOT SIMULATED AI FINDINGS</div>
			</section>
			<section class="panel detail">
				{#if selected}
					<div class="detail-top">
						<div><span class="eyebrow">PERSISTENT LAB CASE</span><h3>{selected.title}</h3><p>{selected.id} · {selectedTenantId} · version {selected.version}</p></div>
						<button type="button" class="secondary" on:click={switchWorkspace}>{mode === 'incidents' ? 'Open analyst casework ↗' : 'Open incident management ↗'}</button>
					</div>
					{#if mode === 'analyst'}
						<div class="notice"><strong>Human investigation, not AI inference</strong>
							<p>Stored notes are authored by lab users; the prototype has no SIEM retrieval, model-generated findings or validated threat attribution.</p></div>
					{/if}
					{#if hasAnalystRole && !canEdit}
						<div class="notice"><strong>Editing requires a fresh lab login</strong>
							<p>Go to API Lab and sign in again for a session-bound CSRF token held only in this page's memory.</p></div>
					{/if}
					<IncidentCaseLab tenantId={selectedTenantId} incident={selected} {csrf} {canEdit} onSaved={loadCases}/>
				{:else}
					<div class="empty-state">Select a server-returned incident to view its case record.</div>
				{/if}
			</section>
		</div>
	{/if}
	<p class="feedback" role="status">{message}</p>
	<footer>RH SENTRY / OPTIONAL LOCAL API VIEW <span>NO LIVE TELEMETRY · NO PRODUCTION CLIENT ACCESS</span></footer>
</div>

<style>
	.local-workspace { color:#eaf0f8 }
	.lab-banner { display:flex;align-items:center;gap:17px;background:linear-gradient(110deg,#29232d,#161d2a);border:1px solid #6b4553;border-radius:10px;padding:19px 22px;margin-bottom:18px }
	.mark { width:44px;height:44px;display:grid;place-items:center;border:1px solid #925165;border-radius:9px;color:#f6a2b2;font-size:25px;flex-shrink:0 }
	.lab-banner strong { font-size:15px }.lab-banner p { font-size:12px;color:#aeb9c6;line-height:1.7;margin:6px 0 0 }
	.lab-status { margin-left:auto;flex-shrink:0;font-size:10px;white-space:nowrap;font-weight:800;color:#f1c09d;border:1px solid #866244;border-radius:5px;padding:9px }
	.lab-status.online { color:#9addbd;border-color:#4e7c69 }
	.stats { display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;margin-bottom:20px }
	.stats>div { background:#111924;border:1px solid #2d3949;border-radius:9px;padding:17px;display:flex;flex-direction:column;gap:9px }
	.stats span { font-size:10px;letter-spacing:.08em;font-weight:750;color:#91a3b8 }.stats strong { font-size:27px }.stats small { font-size:11px;color:#8195aa }
	.toolbar { display:flex;align-items:center;justify-content:space-between;gap:17px;margin:26px 0 19px }
	.toolbar h2 { font-size:20px;margin:9px 0 }.toolbar p { font-size:12px;color:#93a7ba;margin:0 }
	.eyebrow { color:#e16d7e;font-size:10px;font-weight:800;letter-spacing:.11em }
	.buttons { display:flex;gap:9px;flex-wrap:wrap }
	.secondary,.primary { border-radius:6px;cursor:pointer;font-size:11px;font-weight:800;padding:11px 13px;border:1px solid #715163;background:#332633;color:#f1c2cd }
	.secondary:disabled,.primary:disabled { opacity:.35;cursor:not-allowed }.primary { background:#df3550;border-color:#ed556b;color:white }
	.queue-layout { display:grid;grid-template-columns:minmax(250px,.65fr) minmax(480px,1.8fr);gap:15px;align-items:start }
	.panel { background:#111a26;border:1px solid #2c394a;border-radius:10px;min-width:0;overflow:hidden }
	.panel-heading { display:flex;justify-content:space-between;gap:9px;align-items:start;padding:22px }
	.panel-heading h3 { font-size:18px;margin:9px 0 0 }.count { font-size:10px;color:#90a2b6 }
	.controls { padding:0 15px 16px;display:flex;flex-direction:column;gap:9px }
	.controls label { font-size:10px;font-weight:750;color:#9dacc0;letter-spacing:.06em }
	.controls input,.controls select { width:100%;background:#0a121d;color:#e0e8f2;padding:12px;border:1px solid #354455;border-radius:6px;font-size:12px }
	.controls select option { background:#141b27 }
	.queue-rows { max-height:720px;overflow-y:auto }
	.queue-rows button { width:100%;display:block;text-align:left;background:transparent;border:0;border-top:1px solid #2d3949;color:#eaf0f8;padding:17px 19px;cursor:pointer }
	.queue-rows button.chosen { background:#30212e;box-shadow:inset 3px 0 #e9445d }.queue-rows button:hover { background:#263041 }
	.item-top,.item-bottom { display:flex;align-items:center;justify-content:space-between;gap:7px;font-size:11px;color:#92a4b9 }
	.item-top .critical { color:#f47c8f }.queue-rows button strong { display:block;font-size:13px;margin:10px 0;line-height:1.5 }
	.item-bottom { margin:10px 0;color:#c3d0de }.queue-rows small { font-size:11px;color:#90a3b6 }
	.empty-row { font-size:12px;color:#9babbd;line-height:1.65;padding:17px }
	.queue-foot { border-top:1px solid #2a394a;background:#162131;color:#798fa7;font-size:10px;letter-spacing:.06em;padding:15px }
	.detail-top { display:flex;justify-content:space-between;align-items:center;gap:15px;padding:22px }
	.detail-top h3 { font-size:18px;margin:9px 0 }.detail-top p { color:#8ca0b5;font-size:11px;margin:0 }
	.detail> :global(.case-panel) { border-left:0;border-right:0;border-bottom:0;border-radius:0 }
	.notice { margin:0 21px 19px;padding:16px 18px;background:#25242d;border-left:3px solid #bd9065;border-radius:5px }
	.notice strong { font-size:12px;color:#efc29c }.notice p { font-size:12px;line-height:1.7;color:#b5b1bd;margin:8px 0 0 }
	.empty-state { padding:27px;background:#1b2431;border:1px solid #334254;border-radius:9px;color:#aebccc;font-size:12px;line-height:1.8;margin-bottom:15px }
	.empty-state strong { font-size:14px;color:#edf3fa }.empty-state p { font-size:12px;color:#a1b2c4;line-height:1.75 }
	.feedback { color:#9cb0c6;font-size:11px;line-height:1.8;margin:17px 0 }
	.local-workspace footer { display:flex;justify-content:space-between;gap:13px;padding-top:18px;margin-top:25px;border-top:1px solid #29384a;color:#74899d;font-size:10px;font-weight:800;letter-spacing:.07em }
	@media(max-width:1170px){.queue-layout { grid-template-columns:1fr }.stats { grid-template-columns:repeat(2,minmax(0,1fr)) }}
	@media(max-width:750px){.lab-banner,.toolbar,.detail-top { flex-direction:column;align-items:flex-start }.lab-status { margin-left:0 }.local-workspace footer { flex-direction:column }}
	@media(max-width:560px){.stats { grid-template-columns:1fr }}
</style>
