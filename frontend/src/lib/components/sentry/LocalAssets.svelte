<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { chooseLabTenant, visibleLabTenants } from '$lib/sentry-lab/scope';
	import type { LabTenant, LabIdentity, LabCase } from '$lib/sentry-lab/scope';

	/** Tenant-owned fictional inventory, never an agent discovery interface. */
	export let selectedTenantId: string;
	export let labSessionUser: string;
	export let csrf: string;
	export let onOpenApiLab: () => void;
	export let onOpenCase: (tenantId: string, caseId: string) => void;

	type AssetType = 'endpoint' | 'server' | 'network' | 'identity' | 'cloud' | 'application';
	type Criticality = 'low' | 'medium' | 'high' | 'critical';
	type Lifecycle = 'active' | 'maintenance' | 'retired';
	type Asset = {
		id: string; tenantId: string; displayName: string; assetType: AssetType;
		environment: string; owner: string | null; criticality: Criticality;
		lifecycle: Lifecycle; version: number; createdAt: string; updatedAt: string;
		monitoringState: 'not_connected'; lastSeen: null;
	};
	type AssetHistory = {
		id: number; actor: string; action: string; detail: string;
		version: number; occurredAt: string;
	};
	const API = 'http://127.0.0.1:8001';
	const types: AssetType[] = ['endpoint', 'server', 'network', 'identity', 'cloud', 'application'];
	const criticalities: Criticality[] = ['low', 'medium', 'high', 'critical'];
	const lifecycles: Lifecycle[] = ['active', 'maintenance', 'retired'];

	let identity = '';
	let role = '';
	let tenants: LabTenant[] = [];
	let assets: Asset[] = [];
	let selectedAssetId = '';
	let linkedCases: LabCase[] = [];
	let allCases: LabCase[] = [];
	let history: AssetHistory[] = [];
	let online = false;
	let loading = false;
	let fetching = false;
	let busy = false;
	let search = '';
	let error = '';
	let message = '';
	let requestGeneration = 0;
	let detailGeneration = 0;
	let destroyed = false;
	let createOpen = false;

	let newName = '';
	let newType: AssetType = 'endpoint';
	let newEnvironment = 'workstation';
	let newOwner = 'IT team';
	let newCriticality: Criticality = 'medium';
	let newLifecycle: Lifecycle = 'active';

	let editName = '';
	let editType: AssetType = 'endpoint';
	let editEnvironment = '';
	let editOwner = '';
	let editCriticality: Criticality = 'medium';
	let editLifecycle: Lifecycle = 'active';
	let linkIncidentId = '';

	$: selected = assets.find((asset) => asset.id === selectedAssetId) ?? null;
	$: canEdit = Boolean(
		identity && identity === labSessionUser && csrf &&
		(role === 'soc_analyst' || role === 'soc_lead')
	);
	$: matches = assets.filter((asset) =>
		[asset.id, asset.displayName, asset.assetType, asset.environment, asset.owner ?? '',
			asset.criticality, asset.lifecycle].join(' ').toLowerCase().includes(search.trim().toLowerCase())
	);
	$: activeCount = assets.filter((asset) => asset.lifecycle === 'active').length;
	$: needsAttention = assets.filter((asset) => asset.lifecycle === 'maintenance').length;
	$: linkChoices = allCases.filter((item) => !linkedCases.some((linked) => linked.id === item.id));
	$: hasEdits = Boolean(selected && (
		editName !== selected.displayName || editType !== selected.assetType ||
		editEnvironment !== selected.environment || editOwner !== (selected.owner ?? '') ||
		editCriticality !== selected.criticality || editLifecycle !== selected.lifecycle
	));

	async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
		const result = await fetch(API + path, {
			...init, credentials: 'include', cache: 'no-store',
			headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) }
		});
		if (!result.ok) {
			let reason = 'HTTP ' + result.status;
			try {
				const body = await result.json();
				if (typeof body.detail === 'string') reason += ': ' + body.detail;
			} catch { /* Response may not contain JSON. */ }
			throw new Error(reason);
		}
		return (await result.json()) as T;
	}
	function assetPath(id: string) {
		return '/api/tenants/' + encodeURIComponent(selectedTenantId) +
			'/assets/' + encodeURIComponent(id);
	}

	function resetEditor(asset: Asset) {
		editName = asset.displayName;
		editType = asset.assetType;
		editEnvironment = asset.environment;
		editOwner = asset.owner ?? '';
		editCriticality = asset.criticality;
		editLifecycle = asset.lifecycle;
	}

	async function fetchDetails() {
		const serial = ++detailGeneration;
		const tenant = selectedTenantId;
		const asset = assets.find((item) => item.id === selectedAssetId) ?? null;
		linkedCases = [];
		history = [];
		allCases = [];
		linkIncidentId = '';
		if (!tenant || !asset) return;
		try {
			const path = assetPath(asset.id);
			const analyst = role === 'soc_analyst' || role === 'soc_lead';
			const [connections, events, caseList] = await Promise.all([
				request<{tenantId:string; assetId:string; items:LabCase[]}>(path + '/incidents'),
				analyst ? request<{tenantId:string; assetId:string; items:AssetHistory[]}>(path + '/history') :
					Promise.resolve({ tenantId:tenant, assetId:asset.id, items:[] as AssetHistory[] }),
				analyst ? request<{tenantId:string; items:LabCase[]}>(
					'/api/tenants/' + encodeURIComponent(tenant) + '/incidents'
				) : Promise.resolve({ tenantId:tenant, items:[] as LabCase[] })
			]);
			if (destroyed || serial !== detailGeneration || tenant !== selectedTenantId ||
				selectedAssetId !== asset.id) return;
			if (connections.tenantId !== tenant || connections.assetId !== asset.id ||
				events.tenantId !== tenant || events.assetId !== asset.id ||
				caseList.tenantId !== tenant || connections.items.some((x) => x.tenantId !== tenant) ||
				caseList.items.some((x) => x.tenantId !== tenant)) {
				throw new Error('Incorrect customer scope in response; asset details withheld.');
			}
			linkedCases = connections.items;
			history = events.items;
			allCases = caseList.items;
			linkIncidentId = caseList.items.find((x) => !connections.items.some((y) => y.id === x.id))?.id ?? '';
		} catch (err) {
			if (destroyed || serial !== detailGeneration) return;
			linkedCases = [];
			history = [];
			allCases = [];
			error = err instanceof Error ? err.message : 'Unable to load asset associations.';
		}
	}

	async function selectAsset(id: string) {
		selectedAssetId = id;
		const asset = assets.find((item) => item.id === id);
		if (asset) resetEditor(asset);
		await fetchDetails();
	}

	async function fetchAssets(preferredAsset?: string) {
		const serial = ++requestGeneration;
		const tenant = selectedTenantId;
		const previous = preferredAsset ?? selectedAssetId;
		++detailGeneration;
		assets = [];
		selectedAssetId = '';
		linkedCases = [];
		history = [];
		allCases = [];
		error = '';
		message = '';
		fetching = Boolean(tenant);
		if (!tenant) { fetching = false; return; }
		try {
			const response = await request<{
				tenantId:string; source:string; liveSensors:number; items:Asset[];
			}>('/api/tenants/' + encodeURIComponent(tenant) + '/assets');
			if (destroyed || serial !== requestGeneration || tenant !== selectedTenantId) return;
			if (response.tenantId !== tenant || response.source !== 'local-sqlite-fictional' ||
				response.liveSensors !== 0 || response.items.some((asset) =>
					asset.tenantId !== tenant || asset.monitoringState !== 'not_connected'
				)) {
				throw new Error('Unexpected API provenance or tenant scope; inventory withheld.');
			}
			assets = response.items;
			selectedAssetId = assets.some((asset) => asset.id === previous) ?
				previous : assets[0]?.id ?? '';
			const chosen = assets.find((asset) => asset.id === selectedAssetId);
			if (chosen) resetEditor(chosen);
			await fetchDetails();
		} catch (err) {
			if (destroyed || serial !== requestGeneration) return;
			assets = [];
			selectedAssetId = '';
			error = err instanceof Error ? err.message : 'Failed to load the authorised inventory.';
		} finally {
			if (!destroyed && serial === requestGeneration) fetching = false;
		}
	}

	async function connect() {
		const oldTenant = selectedTenantId;
		loading = true;
		identity = '';
		role = '';
		online = false;
		tenants = [];
		assets = [];
		selectedTenantId = '';
		error = '';
		message = '';
		++requestGeneration;
		++detailGeneration;
		try {
			const health = await request<{service:string; mode:string; liveSensors:number}>('/api/health');
			if (health.service !== 'rh-sentry-lab' || health.mode !== 'synthetic-local-only' ||
				health.liveSensors !== 0) throw new Error('Unexpected API service; refusing asset data.');
			online = true;
			const me = await request<LabIdentity>('/api/me');
			const list = await request<{items: LabTenant[]}>('/api/tenants');
			if (destroyed) return;
			identity = me.user;
			tenants = visibleLabTenants(list.items, me.memberships);
			selectedTenantId = chooseLabTenant(tenants, oldTenant);
			role = me.memberships.find((member) => member.tenantId === selectedTenantId)?.role ?? '';
			if (selectedTenantId) await fetchAssets();
			else error = 'No authorised customer asset membership for this fictional account.';
		} catch (err) {
			if (destroyed) return;
			identity = '';
			tenants = [];
			assets = [];
			selectedTenantId = '';
			error = err instanceof Error ? err.message : 'Local API unavailable.';
		} finally {
			if (!destroyed) loading = false;
		}
	}

	function changeTenant() {
		search = '';
		// Never reuse a previous organisation's role on a tenant switch.
		// Refresh role from server before allowing a tenant switch.
		void connectForTenant();
	}
	async function connectForTenant() {
		const tenant = selectedTenantId;
		const serial = ++requestGeneration;
		++detailGeneration;
		assets = []; linkedCases = []; history = []; selectedAssetId = '';
		role = '';
		error = '';
		try {
			const me = await request<LabIdentity>('/api/me');
			if (destroyed || serial !== requestGeneration || tenant !== selectedTenantId) return;
			identity = me.user;
			role = me.memberships.find((member) => member.tenantId === tenant)?.role ?? '';
			if (!role) throw new Error('No membership for selected customer.');
			await fetchAssets();
		} catch (err) {
			if (destroyed) return;
			role = '';
			assets = [];
			error = err instanceof Error ? err.message : 'Unable to validate customer access.';
		}
	}

	async function createAsset() {
		if (!canEdit || busy) return;
		busy = true; error = ''; message = '';
		try {
			const saved = await request<Asset>(
				'/api/tenants/' + encodeURIComponent(selectedTenantId) + '/assets', {
					method: 'POST', headers: {'X-CSRF-Token': csrf},
					body: JSON.stringify({
						displayName:newName.trim(), assetType:newType,
						environment:newEnvironment.trim(), owner:newOwner.trim() || null,
						criticality:newCriticality, lifecycle:newLifecycle
					})
				});
			createOpen = false;
			newName = '';
			await fetchAssets(saved.id);
			message = 'Fictional asset registered in SQLite; monitoring remains not connected.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not register asset.';
		} finally { busy = false; }
	}

	async function saveAsset() {
		const asset = selected;
		if (!asset || !canEdit || busy || !hasEdits) return;
		busy = true; error = ''; message = '';
		try {
			const changes: Record<string, unknown> = {expectedVersion:asset.version};
			if (editName !== asset.displayName) changes.displayName = editName.trim();
			if (editType !== asset.assetType) changes.assetType = editType;
			if (editEnvironment !== asset.environment) changes.environment = editEnvironment.trim();
			if (editOwner !== (asset.owner ?? '')) changes.owner = editOwner.trim() || null;
			if (editCriticality !== asset.criticality) changes.criticality = editCriticality;
			if (editLifecycle !== asset.lifecycle) changes.lifecycle = editLifecycle;
			await request<Asset>(assetPath(asset.id), {
				method: 'PATCH', headers: {'X-CSRF-Token':csrf}, body:JSON.stringify(changes)
			});
			await fetchAssets(asset.id);
			message = 'Asset changes saved with a versioned local audit record.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Asset update failed.';
			if (error.includes('409')) await fetchAssets(asset.id);
		} finally { busy = false; }
	}

	async function linkIncident() {
		const asset = selected;
		if (!asset || !canEdit || !linkIncidentId || busy) return;
		busy = true; error = ''; message = '';
		try {
			await request(assetPath(asset.id) + '/incidents', {
				method: 'POST', headers: {'X-CSRF-Token':csrf},
				body: JSON.stringify({expectedVersion:asset.version, incidentId:linkIncidentId})
			});
			await fetchAssets(asset.id);
			message = 'Existing fictional incident linked to this asset.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not link the incident.';
			if (error.includes('409')) await fetchAssets(asset.id);
		} finally { busy = false; }
	}

	async function unlinkIncident(incidentId: string) {
		const asset = selected;
		if (!asset || !canEdit || busy) return;
		busy = true; error = ''; message = '';
		try {
			await request(assetPath(asset.id) + '/incidents/' + encodeURIComponent(incidentId), {
				method: 'DELETE', headers: {'X-CSRF-Token':csrf},
				body: JSON.stringify({expectedVersion:asset.version})
			});
			await fetchAssets(asset.id);
			message = 'Fictional incident association removed; the incident itself is unchanged.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not unlink the incident.';
			if (error.includes('409')) await fetchAssets(asset.id);
		} finally { busy = false; }
	}

	onMount(() => { void connect(); });
	onDestroy(() => { destroyed = true; ++requestGeneration; ++detailGeneration; });
</script>

<div class="asset-workspace">
	<div class="notice">
		<div class="notice-icon" aria-hidden="true">▣</div>
		<div>
			<strong>Persistent asset inventory · localhost SQLite</strong>
			<p>Register and maintain fictional customer systems, link them to existing investigations and review changes. No endpoint agents, discovery services or real telemetry are connected.</p>
		</div>
		<span class:online class="tag">{online ? 'LOCAL API' : 'OFFLINE'}</span>
	</div>
	<div class="stats">
		<div><span>REGISTERED ASSETS</span><strong>{assets.length.toString().padStart(2, '0')}</strong><small>Persisted fictional records</small></div>
		<div><span>ACTIVE INVENTORY</span><strong>{activeCount.toString().padStart(2, '0')}</strong><small>Lifecycle, not agent health</small></div>
		<div><span>MAINTENANCE</span><strong>{needsAttention.toString().padStart(2, '0')}</strong><small>Administrative lifecycle only</small></div>
		<div><span>LIVE MONITORED</span><strong>00</strong><small>Zero enrolled agents</small></div>
	</div>
	<div class="topbar">
		<div><span class="eyebrow">RH SENTRY / ASSET INTELLIGENCE</span><h2>Customer asset register</h2>
			<p>Lab identity: {identity || 'No session'} · {role || 'Read-only / not authorised'}</p></div>
		<div class="actions">
			{#if canEdit}<button class="primary" type="button" aria-expanded={createOpen} on:click={() => (createOpen = !createOpen)}>{createOpen ? 'Close registration' : '+ Register Asset'}</button>{/if}
			<button class="secondary" type="button" disabled={loading || busy} on:click={() => void connect()}>Refresh API ↻</button>
			<button class="secondary" type="button" on:click={onOpenApiLab}>Open API Lab ↗</button>
		</div>
	</div>
	{#if loading}
		<div class="empty">Authenticating and loading customer asset permissions...</div>
	{:else if !online || !identity || !tenants.length}
		<div class="empty"><strong>Local API access required</strong><p>Start the localhost Python backend and sign in through API Lab to see your fictional customer's asset inventory.</p>
			<button class="primary" type="button" on:click={onOpenApiLab}>Go to API Lab</button></div>
	{:else}
		<div class="scope">
			<label for="asset-tenant">AUTHORISED ORGANISATION</label>
			<select id="asset-tenant" bind:value={selectedTenantId} disabled={busy} on:change={changeTenant}>
				{#each tenants as tenant (tenant.id)}<option value={tenant.id}>{tenant.name}</option>{/each}
			</select>
			<span>ALL ASSET SENSOR STATES: NOT CONNECTED</span>
		</div>
		{#if fetching}
			<div class="empty">Loading tenant-owned asset records...</div>
		{:else}
			<div class="layout">
				<section class="panel catalogue">
					<div class="section-head"><span class="eyebrow">TENANT INVENTORY</span><h3>Registered systems</h3></div>
					<div class="search-area"><label for="asset-search">SEARCH INVENTORY</label>
						<input id="asset-search" type="search" bind:value={search} placeholder="Asset name, lifecycle or owner..."/></div>
					<div class="asset-list">
						{#each matches as item (item.id)}
							<button type="button" class:chosen={selectedAssetId === item.id} aria-pressed={selectedAssetId === item.id} on:click={() => void selectAsset(item.id)}>
								<div class="row-head"><strong>{item.displayName}</strong><span>{item.criticality}</span></div>
								<div class="row-meta">{item.assetType} · {item.environment}</div>
								<div class="row-foot"><span>{item.lifecycle}</span><span>NO AGENT</span></div>
							</button>
						{:else}<div class="empty-inline">No registered assets match this search.</div>{/each}
					</div>
					<div class="catalogue-footer">{assets.length} fictional records · 0 live monitoring integrations</div>
				</section>
				<section class="panel detail">
					{#if selected}
						<div class="section-head"><span class="eyebrow">SELECTED REGISTERED SYSTEM</span><h3>{selected.displayName}</h3><p>{selected.id} · version {selected.version}</p></div>
						<div class="status-note"><strong><span class="point"></span> Monitoring not connected</strong>
							<p>Inventory status does not indicate a live sensor, detection coverage, successful scan or assurance rating.</p></div>
						<div class="details-grid">
							<div><span>TYPE</span><strong>{selected.assetType}</strong></div>
							<div><span>CRITICALITY</span><strong>{selected.criticality}</strong></div>
							<div><span>LIFECYCLE</span><strong>{selected.lifecycle}</strong></div>
							<div><span>OWNER</span><strong>{selected.owner ?? 'Unassigned'}</strong></div>
						</div>
						{#if canEdit}
							<div class="form-section"><div class="eyebrow">ASSET CONTROL / ANALYST ONLY</div><h4>Update this asset</h4>
								<div class="edit-grid">
									<label>Name<input bind:value={editName} maxlength="80"/></label>
									<label>Type<select bind:value={editType}>{#each types as type}<option value={type}>{type}</option>{/each}</select></label>
									<label>Environment<input bind:value={editEnvironment} maxlength="50"/></label>
									<label>Owner<input bind:value={editOwner} maxlength="60"/></label>
									<label>Criticality<select bind:value={editCriticality}>{#each criticalities as risk}<option value={risk}>{risk}</option>{/each}</select></label>
									<label>Lifecycle<select bind:value={editLifecycle}>{#each lifecycles as state}<option value={state}>{state}</option>{/each}</select></label>
								</div>
								<button class="primary" type="button" disabled={!hasEdits || busy} on:click={saveAsset}>Save asset changes</button>
								<p class="minor">A stale record version is rejected by the server. Retiring an asset doesn't remove historical evidence.</p>
							</div>
						{:else}
							<div class="readonly">Read-only customer view. Asset edits require a fictional SOC analyst session and fresh CSRF token from API Lab.</div>
						{/if}
						<div class="form-section"><div class="eyebrow">INVESTIGATION CONTEXT</div><h4>Linked incidents</h4>
							{#each linkedCases as linked (linked.id)}
								<div class="related">
									<div><strong>{linked.title}</strong><small>{linked.id} · {linked.status} · {linked.severity}</small></div>
									<div class="related-buttons"><button class="secondary" type="button" on:click={() => onOpenCase(selectedTenantId, linked.id)}>Open case ↗</button>
										{#if canEdit}<button class="secondary" disabled={busy} type="button" on:click={() => void unlinkIncident(linked.id)}>Unlink</button>{/if}</div>
								</div>
							{:else}<p class="minor">No fictional investigations are linked to this system.</p>{/each}
							{#if canEdit && linkChoices.length}
								<label class="link-picker" for="asset-link-case">LINK EXISTING TENANT INCIDENT
									<select id="asset-link-case" bind:value={linkIncidentId}>
										{#each linkChoices as option (option.id)}<option value={option.id}>{option.id} · {option.title}</option>{/each}
									</select>
								</label>
								<button type="button" class="primary" disabled={!linkIncidentId || busy} on:click={linkIncident}>Link incident</button>
							{/if}
						</div>
						{#if canEdit}
							<div class="form-section"><div class="eyebrow">VERSIONED AUDIT JOURNAL</div><h4>Asset history</h4>
								{#each history as event (event.id)}
									<div class="audit-entry"><strong>{event.action} · v{event.version}</strong>
										<p>{event.detail}</p><small>{event.actor} · {event.occurredAt}</small></div>
								{:else}<p class="minor">This seed record has no user-generated changes yet.</p>{/each}
							</div>
						{/if}
					{:else}<div class="empty">Select a registered fictional asset to view its details and linked investigations.</div>{/if}
				</section>
			</div>

			{#if canEdit && createOpen}
				<div class="create-container">
					<div class="panel new-asset">
						<span class="eyebrow">FICTIONAL INVENTORY / ANALYST INPUT</span><h3>Register a training asset</h3>
						<div class="edit-grid">
								<label>Name<input bind:value={newName} maxlength="80" placeholder="TRAINING-WIN-42"/></label>
								<label>Type<select bind:value={newType}>{#each types as type}<option value={type}>{type}</option>{/each}</select></label>
								<label>Environment<input bind:value={newEnvironment} maxlength="50"/></label>
								<label>Owner<input bind:value={newOwner} maxlength="60"/></label>
								<label>Criticality<select bind:value={newCriticality}>{#each criticalities as risk}<option value={risk}>{risk}</option>{/each}</select></label>
								<label>Lifecycle<select bind:value={newLifecycle}>{#each lifecycles as state}<option value={state}>{state}</option>{/each}</select></label>
							</div>
							<button type="button" class="primary" disabled={busy || newName.trim().length < 3} on:click={createAsset}>{busy ? 'Saving...' : 'Register fictional asset'}</button>
							<p class="minor">Use fictional names only. This creates an inventory record, not an agent or monitor.</p>
						</div>
				</div>
			</div>
			{/if}
		{/if}
	{/if}
	{#if message}<p class="feedback" role="status">{message}</p>{/if}
	{#if error}<p class="feedback error" role="alert">{error}</p>{/if}
	<footer>RH SENTRY / PERSISTENT FICTIONAL ASSETS <span>NO ASSET DISCOVERY · NO LIVE COVERAGE · NO AUTOMATED ACTIONS</span></footer>
</div>

<style>
	.asset-workspace{color:#eaf1f8}
	.notice{display:flex;align-items:center;gap:17px;background:linear-gradient(110deg,#2c2330,#151d29);border:1px solid #765363;border-radius:10px;padding:19px;margin-bottom:17px}
	.notice-icon{width:44px;height:44px;display:grid;place-items:center;border:1px solid #a05a6e;border-radius:9px;color:#f4a2b5;font-size:25px;flex-shrink:0}
	.notice strong{font-size:14px}.notice p{color:#adbaca;font-size:12px;line-height:1.75;margin:7px 0 0}
	.tag{border:1px solid #876346;color:#e4bc95;font-size:10px;padding:9px;border-radius:5px;margin-left:auto;white-space:nowrap;font-weight:800}
	.tag.online{border-color:#42745f;color:#8dd7b2}
	.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:19px}
	.stats>div{display:flex;flex-direction:column;gap:10px;background:#121a27;border:1px solid #303d4d;border-radius:8px;padding:18px}
	.stats span{font-size:10px;letter-spacing:.06em;color:#91a5bc;font-weight:800}.stats strong{font-size:28px}.stats small{color:#8e9eb1;font-size:11px}
	.topbar{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:24px 0}
	.topbar h2{font-size:23px;margin:9px 0}.topbar p{font-size:12px;color:#8fa4ba;margin:0}
	.eyebrow{font-size:10px;letter-spacing:.12em;color:#ec7487;font-weight:800}.actions{display:flex;gap:9px;flex-wrap:wrap}
	.primary,.secondary{cursor:pointer;border:1px solid #775368;border-radius:6px;padding:11px 14px;font-size:11px;font-weight:800;background:#372634;color:#f1bfca}
	.primary{background:#df3653;color:#fff;border-color:#ec4964}.primary:disabled,.secondary:disabled{opacity:.42;cursor:not-allowed}
	.scope{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:14px;background:#142030;border:1px solid #344558;border-radius:8px;margin:15px 0}
	.scope label,.scope span{font-size:10px;letter-spacing:.08em;color:#91a9c0;font-weight:750}.scope span{margin-left:auto}
	select,input{background:#09131e;color:#f0f4f8;border:1px solid #35485c;border-radius:6px;padding:11px 12px;font-size:12px;min-width:0;width:100%}
	.scope select{width:auto;min-width:220px;max-width:100%}
	.layout{display:grid;grid-template-columns:minmax(250px,.7fr) minmax(470px,1.7fr);gap:15px;align-items:start}
	.panel{background:#111a27;border:1px solid #304053;border-radius:9px;min-width:0;overflow:hidden}
	.section-head{padding:22px;border-bottom:1px solid #2b3c4d}
	.section-head h3{font-size:19px;margin:8px 0 0}.section-head p{color:#879cb1;font-size:11px;margin:9px 0 0}
	.search-area{padding:18px;display:flex;flex-direction:column;gap:9px}.search-area label{font-size:10px;letter-spacing:.08em;font-weight:750;color:#a7b7cb}
	.asset-list{max-height:650px;overflow-y:auto}
	.asset-list button{cursor:pointer;background:transparent;color:#e9eff7;border:0;border-top:1px solid #28394a;text-align:left;width:100%;display:block;padding:18px}
	.asset-list button.chosen{box-shadow:inset 3px 0 #e74f67;background:#352631}.asset-list button:hover{background:#223044}
	.row-head,.row-foot{display:flex;justify-content:space-between;gap:10px}
	.row-head strong{font-size:12px;overflow-wrap:anywhere}.row-head span{font-size:10px;color:#f1b3bd;text-transform:uppercase}
	.row-meta{font-size:11px;color:#abbacd;margin:10px 0}.row-foot{font-size:10px;color:#7f98b0;font-weight:750}
	.catalogue-footer{padding:15px;background:#182437;color:#8b9fb2;font-size:10px}
	.status-note{margin:18px 21px;background:#2b2730;border-left:3px solid #bd8d6b;padding:16px}
	.status-note strong{font-size:12px;color:#f1c19b}.status-note p{color:#b9b3bf;font-size:11px;line-height:1.7;margin:7px 0 0}
	.point{display:inline-block;width:7px;height:7px;border-radius:50%;background:#e5a763;margin-right:5px}
	.details-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;padding:0 21px 19px}
	.details-grid>div{border:1px solid #2b3e51;border-radius:7px;background:#0d1521;padding:13px;display:flex;flex-direction:column;gap:8px}
	.details-grid span{color:#8ca2b8;font-size:9px;font-weight:800;letter-spacing:.07em}.details-grid strong{font-size:12px;overflow-wrap:anywhere;text-transform:capitalize}
	.form-section{margin:0 21px 19px;border:1px solid #29394b;padding:19px;background:#0d1522;border-radius:8px}
	.form-section h4{font-size:17px;margin:10px 0 17px}.edit-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:10px 0 17px}
	.edit-grid label,.link-picker{display:flex;flex-direction:column;gap:8px;color:#a9bfd0;font-size:10px;letter-spacing:.03em;font-weight:750}
	.minor{color:#91a7b9;font-size:11px;line-height:1.7;margin:13px 0}
	.readonly{padding:17px;margin:0 21px 19px;background:#27252e;border-left:3px solid #b78c6a;color:#cfb4b6;font-size:11px;line-height:1.7}
	.related{display:flex;align-items:center;justify-content:space-between;gap:13px;padding:14px 0;border-top:1px solid #2b3d4c}
	.related strong{font-size:12px}.related small{font-size:11px;color:#9db0c1;display:block;margin-top:8px}.related-buttons{display:flex;flex-wrap:wrap;gap:7px}
	.link-picker{margin:15px 0}.audit-entry{border-top:1px solid #2a394a;padding:14px 0}
	.audit-entry strong{font-size:12px}.audit-entry p{color:#adbac7;font-size:11px;line-height:1.7}.audit-entry small{color:#8497ae;font-size:10px}
	.create-container{margin-top:22px}.new-asset{padding:21px;margin-top:15px}.new-asset h3{font-size:18px}
	.empty,.empty-inline{padding:23px;background:#182434;border:1px solid #334253;color:#a9bccd;border-radius:7px;font-size:12px;line-height:1.7}
	.empty strong{display:block;font-size:14px;color:#f5f8fc}.empty-inline{background:transparent;border:0}
	.feedback{margin-top:16px;background:#1d2b2f;border:1px solid #3a6264;color:#abd4d0;padding:14px;border-radius:7px;font-size:12px}
	.feedback.error{background:#30252b;border-color:#885462;color:#f5b9c5}
	.asset-workspace footer{border-top:1px solid #2a394b;margin-top:22px;padding-top:17px;display:flex;justify-content:space-between;gap:12px;color:#748da5;font-size:10px;font-weight:800;letter-spacing:.07em}
	@media(max-width:1190px){.layout{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
	@media(max-width:800px){.notice,.topbar{flex-direction:column;align-items:flex-start}.tag{margin-left:0}.details-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.asset-workspace footer{flex-direction:column}}
	@media(max-width:550px){.stats{grid-template-columns:1fr}.edit-grid{grid-template-columns:1fr}.scope select{width:100%}.related{flex-direction:column;align-items:flex-start}}
</style>
