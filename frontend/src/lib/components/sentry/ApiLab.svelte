<script lang="ts">
	import { onMount } from 'svelte';
	import IncidentCaseLab from '$lib/components/sentry/IncidentCaseLab.svelte';
	export let sharedSession: { user: string; csrf: string } | null;
	export let onSessionChange: (next: { user: string; csrf: string } | null) => void;

	// This screen only talks to an explicitly local, separately started API lab.
	// There is no production endpoint, browser persistence or active SOC service.
	const API = 'http://127.0.0.1:8001';
	const users = [
		{ id: 'alderwick-viewer', title: 'Alderwick — customer viewer' },
		{ id: 'alderwick-analyst', title: 'Alderwick — SOC analyst' },
		{ id: 'alderwick-lead', title: 'Alderwick — SOC lead' },
		{ id: 'harbourline-viewer', title: 'Harbourline — customer viewer' },
		{ id: 'summit-viewer', title: 'Summit — customer viewer' },
		{ id: 'lab-auditor', title: 'Lab auditor — metadata and log only' }
	];
	type Tenant = { id: string; name: string };
	type Incident = { id: string; tenantId: string; title: string; severity: string; status: string; version: number; assignedTo: string | null };
	type AuditEntry = { id: number; actor: string; tenant_id: string | null; operation: string; outcome: string; occurred_at: string };
	let selectedUser = users[0].id;
	let password = '';
	let csrf = '';
	let sessionUser = '';
	let online = false;
	let checked = false;
	let busy = false;
	let status = '';
	let tenants: Tenant[] = [];
	let permittedTenants: Tenant[] = [];
	let tenantRoles: Record<string, string> = {};
	let selectedIncidentId = '';
	let tenantId = '';
	let incidents: Incident[] = [];
	let audit: AuditEntry[] = [];
	let denialStatus = '';
	let requestedTenant = 'summit';
	$: canEdit = ['soc_analyst', 'soc_lead'].includes(tenantRoles[tenantId] ?? '');
	$: selectedIncident = incidents.find((item) => item.id === selectedIncidentId) ?? null;

	async function callApi(path: string, options: RequestInit = {}) {
		const result = await fetch(API + path, {
			...options,
			credentials: 'include',
			cache: 'no-store',
			headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) }
		});
		if (!result.ok) {
			let detail = 'HTTP ' + result.status;
			try {
				const payload = await result.json();
				if (typeof payload.detail === 'string') detail += ': ' + payload.detail;
			} catch { /* Unknown error document; keep generic status. */ }
			throw new Error(detail);
		}
		return result.json();
	}

	async function checkServer() {
		try {
			const health = await callApi('/api/health');
			online = health.mode === 'synthetic-local-only' && health.liveSensors === 0;
			status = online ? 'Local API responded. No live monitoring is connected.' : 'The service was not identified as the RH Sentry lab.';
		} catch {
			online = false;
			status = 'The local API is offline. Follow the setup commands below before attempting to log in.';
		}
		checked = true;
	}

	async function refreshSession() {
		try {
			const me = await callApi('/api/me');
			sessionUser = me.user;
			const result = await callApi('/api/tenants');
			tenants = result.items as Tenant[];
			const memberships = me.memberships as {tenantId: string; role: string}[];
			tenantRoles = Object.fromEntries(memberships.map((x) => [x.tenantId, x.role]));
			const allowedIds = new Set(memberships.map((x) => x.tenantId));
			permittedTenants = tenants.filter((tenant) => allowedIds.has(tenant.id));
			tenantId = permittedTenants[0]?.id ?? '';
			if (tenantId) await loadIncidents();
			else incidents = [];
		} catch (error) {
			sessionUser = '';
			tenants = [];
			permittedTenants = [];
			tenantRoles = {};
			selectedIncidentId = '';
			tenantId = '';
			incidents = [];
			throw error;
		}
	}

	async function login() {
		if (!online || !password || busy) return;
		busy = true;
		status = '';
		try {
			const result = await callApi('/api/lab/login', {
				method: 'POST',
				body: JSON.stringify({ username: selectedUser, password })
			});
			csrf = result.csrfToken;
			await refreshSession();
			onSessionChange({ user: sessionUser, csrf });
			status = 'Signed in to the local lab as ' + sessionUser + '. The session is not a production identity.';
		} catch (error) {
			status = error instanceof Error ? error.message : 'Local lab login failed.';
		} finally {
			password = '';
			busy = false;
		}
	}

	async function logout() {
		if (busy) return;
		busy = true;
		try {
			await callApi('/api/lab/logout', { method: 'POST', headers: { 'X-CSRF-Token': csrf } });
			status = 'Local lab session revoked.';
			onSessionChange(null);
			csrf = '';
			sessionUser = '';
			tenants = [];
			permittedTenants = [];
			tenantRoles = {};
			selectedIncidentId = '';
			incidents = [];
			audit = [];
			tenantId = '';
		} catch (error) {
			status = 'The server did not confirm session revocation: ' +
				(error instanceof Error ? error.message : 'unknown error');
		} finally {
			busy = false;
		}
	}

	async function loadIncidents() {
		if (!tenantId) { incidents = []; return; }
		try {
			const result = await callApi('/api/tenants/' + encodeURIComponent(tenantId) + '/incidents');
			incidents = result.items as Incident[];
			if (!incidents.some((item) => item.id === selectedIncidentId)) selectedIncidentId = incidents[0]?.id ?? '';
			status = 'Only incidents returned by the authenticated server-side tenant query are displayed.';
		} catch (error) {
			incidents = [];
			selectedIncidentId = '';
			status = error instanceof Error ? error.message : 'Could not load lab incidents.';
		}
	}

	async function testDenial() {
		if (!sessionUser) return;
		denialStatus = '';
		try {
			await callApi('/api/tenants/' + encodeURIComponent(requestedTenant) + '/incidents');
			denialStatus = 'Allowed by the lab API. Check membership and selected tenant; this may be expected for the selected account.';
		} catch (error) {
			denialStatus = error instanceof Error ? 'Server denied request: ' + error.message : 'Server denied request.';
		}
	}

	async function loadAudit() {
		if (sessionUser !== 'lab-auditor') return;
		try {
			const result = await callApi('/api/lab/audit');
			audit = result.items as AuditEntry[];
			status = 'Loaded persisted fictional audit events from local SQLite.';
		} catch (error) {
			status = error instanceof Error ? error.message : 'Could not load audit.';
		}
	}

	onMount(() => {
		void checkServer();
		if (sharedSession) {
			csrf = sharedSession.csrf;
			void refreshSession().catch(() => onSessionChange(null));
		}
	});
</script>

<div class="api-lab">
	<div class="banner">
		<div class="banner-icon" aria-hidden="true">⌘</div>
		<div><strong>Local API integration laboratory</strong><p>Connect to a separately running Python API on your laptop, using fictional accounts and SQLite. This is not an internet-ready security service, and it has no production credentials.</p></div>
		<span class:connected={online} class="status-label">{online ? 'LOCAL API ONLINE' : 'NO API CONNECTION'}</span>
	</div>

	<div class="metrics">
		<div><span>LIVE TELEMETRY</span><strong>00</strong><small>No agents connected</small></div>
		<div><span>PRODUCTION CUSTOMERS</span><strong>00</strong><small>Fictional sample tenants only</small></div>
		<div><span>AUTHENTICATED LAB SESSION</span><strong>{sessionUser ? 'YES' : 'NO'}</strong><small>Temporary local session</small></div>
		<div><span>LOCAL DATABASE</span><strong>SQLite</strong><small>On your device only</small></div>
	</div>

	<div class="grid">
		<section class="panel">
			<div class="panel-heading"><div><span class="eyebrow">ENVIRONMENT / LOCAL ONLY</span><h2>Connect to RH Sentry Lab</h2></div><button type="button" class="secondary" on:click={checkServer}>Check API ↻</button></div>
			<div class="connection"><span>API ADDRESS</span><code>{API}</code><strong class:okay={online}>{online ? 'Responding' : checked ? 'Not connected' : 'Checking...'}</strong></div>
			{#if !online}
				<div class="setup">
					<strong>Start your local test backend</strong>
					<p>In a new VS Code terminal, from the repository root:</p>
					<pre>cd dev\rh_sentry_lab_api
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$secret = Read-Host "Create temporary lab password" -AsSecureString
$env:RH_SENTRY_LAB_PASSWORD = [System.Net.NetworkCredential]::new("", $secret).Password
.\.venv\Scripts\python.exe run.py</pre>
					<p>Use a unique password of at least 16 characters. Keep it local and never use real customer credentials. You can then select a fictional user below and enter the same temporary password.</p>
				</div>
			{/if}
			{#if !sessionUser}
				<form on:submit|preventDefault={login} class="form">
					<label for="lab-user">FICTIONAL LAB IDENTITY</label>
					<select id="lab-user" bind:value={selectedUser}>{#each users as u}<option value={u.id}>{u.title}</option>{/each}</select>
					<label for="lab-password">TEMPORARY LOCAL PASSWORD</label>
					<input id="lab-password" type="password" autocomplete="off" bind:value={password} placeholder="Your local lab password (never a company password)" />
					<button type="submit" class="primary" disabled={!online || !password || busy}>{busy ? 'Connecting...' : 'Log in to local lab'}</button>
				</form>
			{:else}
				<div class="session">
					<div><span>AUTHENTICATED LAB USER</span><strong>{sessionUser}</strong></div>
					<button type="button" class="secondary" disabled={busy} on:click={logout}>Revoke session</button>
				</div>
			{/if}
			<div class="message" role="status">{status}</div>
		</section>

		<section class="panel">
			<div class="panel-heading"><div><span class="eyebrow">SERVER-ENFORCED TENANT QUERY</span><h2>Incident records</h2></div><span class="demo-label">SYNTHETIC DATA</span></div>
			{#if !sessionUser}
				<div class="placeholder"><span aria-hidden="true">⌁</span><h3>No authenticated session</h3><p>Log in with a fictional identity to retrieve incidents from the local SQLite database. The browser cannot choose or invent a tenant membership.</p></div>
			{:else if !permittedTenants.length}
				<div class="placeholder"><span aria-hidden="true">◇</span><h3>No tenant membership</h3><p>The selected lab identity can view organisation metadata only, not customer incident records.</p></div>
			{:else}
				<div class="tenant-selector">
					<label for="lab-tenant">AUTHORISED TENANT</label>
					<select id="lab-tenant" bind:value={tenantId} on:change={loadIncidents}>
						{#each permittedTenants as t}<option value={t.id}>{t.name}</option>{/each}
					</select>
				</div>
				<div class="incidents">
					{#each incidents as incident (incident.id)}
						<button type="button" class="incident" class:chosen={selectedIncidentId === incident.id} aria-pressed={selectedIncidentId === incident.id} on:click={() => (selectedIncidentId = incident.id)}><span class="severity" class:critical={incident.severity === 'critical'}>{incident.severity}</span><span class="incident-summary"><strong>{incident.title}</strong><small>{incident.id} · {incident.status} · v{incident.version} · {incident.assignedTo ?? 'Unassigned'}</small></span><span class="case-arrow" aria-hidden="true">›</span></button>
					{:else}
						<div class="placeholder">No fictional incidents returned for this tenant.</div>
					{/each}
				</div>
				<div class="tenant-foot">The API checks membership and filters records in SQL. This page does not perform client-side tenant filtering.</div>
			{/if}
		</section>
	</div>

	{#if sessionUser && tenantId && selectedIncident}
		<div class="case-workspace"><IncidentCaseLab {tenantId} incident={selectedIncident} {csrf} {canEdit} onSaved={loadIncidents} /></div>
	{/if}

	<div class="grid second">
		<section class="panel tests">
			<div class="panel-heading"><div><span class="eyebrow">CROSS-TENANT REJECTION CHECK</span><h2>Try an unauthorised request</h2></div></div>
			<p>Choose a different fictional tenant and ask the API for its incidents. The server should return HTTP 404 when your identity has no membership. No information from the other customer is included in the response.</p>
			<label for="other-tenant">REQUESTED TENANT</label>
			<select id="other-tenant" bind:value={requestedTenant}>{#each ['summit','alderwick','harbourline'] as id}<option value={id}>{id}</option>{/each}</select>
			<button type="button" class="secondary" disabled={!sessionUser} on:click={testDenial}>Send lab request</button>
			{#if denialStatus}<div class="result" role="status">{denialStatus}</div>{/if}
		</section>
		<section class="panel tests">
			<div class="panel-heading"><div><span class="eyebrow">DATABASE EVENT JOURNAL</span><h2>Local audit trail</h2></div></div>
			<p>Successful and denied reads are written to local SQLite. This is a demonstration journal, not tamper-resistant production auditing.</p>
			<button type="button" class="secondary" disabled={sessionUser !== 'lab-auditor'} on:click={loadAudit}>Load local audit events</button>
			{#if sessionUser !== 'lab-auditor'}<p class="audit-note">Log in as the fictional lab auditor to inspect the journal. Platform metadata access does not grant customer incident access.</p>{/if}
			<div class="audit-list">
				{#each audit.slice(0,12) as entry (entry.id)}
					<div><strong>{entry.outcome} / {entry.operation}</strong><small>{entry.actor} · {entry.tenant_id ?? 'platform'} · {entry.occurred_at}</small></div>
				{/each}
			</div>
		</section>
	</div>
	<footer>RH SENTRY · ISOLATED LOCAL API LAB <span>NO REAL CLIENTS · NO LIVE SENSORS · NOT FOR PRODUCTION</span></footer>
</div>

<style>
	.api-lab{color:#eaf0f8}
	.banner{display:flex;align-items:center;gap:17px;border:1px solid #68535a;border-radius:10px;background:linear-gradient(110deg,#27232e,#151d29);padding:20px;margin-bottom:18px}
	.banner-icon{display:grid;place-items:center;width:44px;height:44px;border-radius:9px;border:1px solid #824659;color:#f2aab8;font-size:25px;flex-shrink:0}
	.banner strong{font-size:15px}.banner p{font-size:12px;line-height:1.75;color:#afb9c6;margin:6px 0 0}
	.status-label{margin-left:auto;flex-shrink:0;color:#f2c08a;border:1px solid #806347;border-radius:5px;padding:9px;font-size:10px;font-weight:800}
	.status-label.connected{color:#9de0c0;border-color:#467e69}
	.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:25px}
	.metrics>div{display:flex;flex-direction:column;gap:10px;padding:19px;background:#121a25;border:1px solid #293848;border-radius:9px}
	.metrics span,.connection span,.session span,.tenant-selector label,.form label,.tests>label{font-size:10px;font-weight:800;letter-spacing:.08em;color:#94a6bc}
	.metrics strong{font-size:28px}.metrics small{color:#8698ae;font-size:11px}
	.grid{display:grid;grid-template-columns:minmax(300px,1fr) minmax(400px,1.45fr);gap:15px;align-items:start}
	.grid.second{margin-top:15px;grid-template-columns:repeat(2,minmax(0,1fr))}
	.panel{background:#111a26;border:1px solid #2d394b;border-radius:10px;min-width:0;overflow:hidden}
	.panel-heading{display:flex;align-items:start;justify-content:space-between;gap:10px;padding:23px}
	.panel-heading h2{font-size:19px;margin:9px 0 0;font-weight:770}
	.eyebrow{font-size:10px;font-weight:800;letter-spacing:.12em;color:#dc6273}
	.secondary,.primary{border-radius:6px;border:1px solid #714959;background:#362533;color:#f2c4ce;padding:12px;font-size:11px;font-weight:800;cursor:pointer}
	.primary{background:#de3951;border-color:#f25368;color:white}
	.secondary:disabled,.primary:disabled{cursor:not-allowed;opacity:.35}
	.connection{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 22px 17px;padding:14px;background:#0b1420;border:1px solid #314054;border-radius:7px}
	.connection code{font-size:12px;color:#c6d7e8}.connection strong{font-size:11px;margin-left:auto;color:#f5b586}
	.connection strong.okay{color:#8fe5ba}
	.setup{padding:19px;margin:0 22px 17px;border-radius:8px;background:#1d2735;border:1px solid #3e4a5d}
	.setup strong{font-size:13px}.setup p,.tests p{font-size:12px;line-height:1.75;color:#a3b3c6}
	.setup pre{background:#0a111b;border:1px solid #344458;color:#bad5ed;white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px;padding:14px;line-height:1.75}
	.form{display:flex;flex-direction:column;gap:11px;padding:0 22px 22px}
	.form select,.form input,.tenant-selector select,.tests select{width:100%;min-width:0;background:#0b1421;border:1px solid #34465b;padding:12px;border-radius:6px;color:#dce6f2;font-size:12px}
	.form select option,.tenant-selector option,.tests option{background:#101a28}
	.session{margin:0 22px 20px;display:flex;align-items:center;justify-content:space-between;gap:10px}
	.session div{display:flex;flex-direction:column;gap:7px}.session strong{font-size:14px}
	.message{margin:0 22px 22px;color:#d0b5a2;font-size:11px;line-height:1.6;min-height:16px}
	.demo-label{border:1px solid #714a5b;background:#392532;color:#f7c0cc;padding:8px;font-size:10px;border-radius:5px;white-space:nowrap}
	.placeholder{padding:45px 27px;text-align:center;color:#a2b1c5;font-size:12px}
	.placeholder span{font-size:36px;color:#dd6072}
	.placeholder h3{font-size:16px;color:#eff3f9;margin:13px 0 7px}
	.placeholder p{font-size:12px;line-height:1.75}
	.tenant-selector{padding:0 22px 17px;display:flex;flex-direction:column;gap:8px}
	.incident{border:0;border-top:1px solid #2b394b;padding:17px 22px;display:flex;gap:14px;align-items:center;width:100%;background:transparent;color:#e8eff8;text-align:left;cursor:pointer}
	.incident:hover{background:#1e2a3a}.incident.chosen{background:#342331;box-shadow:inset 3px 0 #e84e63}
	.incident-summary{min-width:0;flex:1}.case-arrow{color:#f08093;font-size:19px}
	.case-workspace{margin-top:18px}
	.incident strong{font-size:13px}.incident small{font-size:11px;color:#8a9db2;display:block;margin-top:7px}
	.severity{text-transform:uppercase;border:1px solid #7a523c;background:#402e27;color:#ecc18b;border-radius:5px;padding:7px 9px;font-size:9px;font-weight:800}
	.severity.critical{color:#ffaab8;background:#4b2634;border-color:#8b4358}
	.tenant-foot{padding:16px 22px;font-size:11px;line-height:1.6;background:#182233;color:#98a9bd}
	.tests{padding-bottom:22px}
	.tests>p,.tests>label,.tests>select,.tests>button,.tests>.result,.tests>.audit-note{display:block;margin:0 22px 15px}
	.tests>select{width:calc(100% - 44px)}
	.result{font-size:12px;color:#f0ca9a;background:#342b27;border:1px solid #685342;padding:15px;border-radius:6px;line-height:1.7}
	.audit-note{color:#b5a8a7!important}
	.audit-list{margin:0 22px;max-height:250px;overflow-y:auto}
	.audit-list>div{border-top:1px solid #2a394a;padding:11px 0;display:flex;flex-direction:column;gap:6px}
	.audit-list strong{font-size:12px}.audit-list small{font-size:10px;color:#9eafc2}
	.api-lab footer{display:flex;justify-content:space-between;gap:10px;border-top:1px solid #2b3747;padding-top:19px;margin-top:26px;color:#72849b;font-size:10px;font-weight:750;letter-spacing:.08em}
	@media(max-width:1120px){.grid,.grid.second{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
	@media(max-width:680px){.banner{flex-wrap:wrap}.status-label{margin-left:0}.metrics{grid-template-columns:1fr}.api-lab footer{flex-direction:column}}
</style>
