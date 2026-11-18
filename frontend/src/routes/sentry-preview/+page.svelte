<script lang="ts">
	import { onMount } from 'svelte';
	import { canonicalSentryPreviewPath } from '$lib/sentry-contracts/preview-url';
	import AnalystWorkspace from '$lib/components/sentry/AnalystWorkspace.svelte';
	import CustomerPortfolio from '$lib/components/sentry/CustomerPortfolio.svelte';
	import ResponseCentre from '$lib/components/sentry/ResponseCentre.svelte';
	import LocalResponseCentre from '$lib/components/sentry/LocalResponseCentre.svelte';
	import PlatformGuide from '$lib/components/sentry/PlatformGuide.svelte';
	import { getGuide } from '$lib/sentry-contracts/platform-guide';
	import type { SentryView } from '$lib/sentry-contracts/platform-guide';
	import DetectionEngineering from '$lib/components/sentry/DetectionEngineering.svelte';
	import PlatformSecurity from '$lib/components/sentry/PlatformSecurity.svelte';
	import ApiLab from '$lib/components/sentry/ApiLab.svelte';
	import LocalCaseWorkspace from '$lib/components/sentry/LocalCaseWorkspace.svelte';
	import LocalCommandCentre from '$lib/components/sentry/LocalCommandCentre.svelte';
	import LocalAssets from '$lib/components/sentry/LocalAssets.svelte';
	import LocalDetectionEngineering from '$lib/components/sentry/LocalDetectionEngineering.svelte';
	import SyntheticEventPipeline from '$lib/components/sentry/SyntheticEventPipeline.svelte';
	import type { DemoIncident as Incident, Severity, IncidentStatus as Status } from '$lib/sentry-demo/types';
	// RH Sentry product-design sandbox. Core modules use simulated data.
	// The optional API Lab is explicitly local-only; no real-world SOC response
	// actions, production accounts, or live security integrations are connected.
	type View = SentryView;
	const seed: Incident[] = [
		{
			id: 'SEN-2048',
			tenantId: 'alderwick',
			title: 'Impossible travel authentication',
			category: 'Identity & access',
			asset: 'M365 / alex.morgan@demo.invalid',
			severity: 'Critical',
			status: 'Investigating',
			time: '14:32',
			description: 'Two sign-ins attributed to the same demonstration account originate from geographically distant sources within a short interval. Additional evidence is required before concluding compromise.',
			confidence: 91,
			indicators: ['Sign-ins 4 minutes apart', 'Previously unseen device fingerprint', 'MFA challenge recorded'],
			timeline: ['14:28 · Sign-in from familiar device', '14:32 · Unusual sign-in detected', '14:33 · Risk rule correlated two events']
		},
		{
			id: 'SEN-2047',
			tenantId: 'alderwick',
			title: 'Suspicious PowerShell execution',
			category: 'Endpoint activity',
			asset: 'WIN-DEMO-07',
			severity: 'High',
			status: 'Awaiting review',
			time: '13:54',
			description: 'An encoded PowerShell command was observed on a demo workstation. The script content and parent process need analyst validation.',
			confidence: 84,
			indicators: ['Encoded command line', 'Unusual parent process', 'No confirmed malicious payload'],
			timeline: ['13:52 · Process created', '13:54 · Detection rule triggered', '13:56 · Evidence collected for review']
		},
		{
			id: 'SEN-2046',
			tenantId: 'summit',
			title: 'Multiple blocked inbound connections',
			category: 'Network defence',
			asset: 'FW-EDGE-DEMO-01',
			severity: 'Medium',
			status: 'Contained',
			time: '12:18',
			description: 'Firewall policy blocked repeated inbound requests to a non-public service. No successful connection is evidenced in the sample.',
			confidence: 95,
			indicators: ['38 denied connections', 'Single external source', 'No accepted sessions observed'],
			timeline: ['12:15 · First connection denied', '12:18 · Burst threshold reached', '12:20 · Demo investigation closed']
		},
		{
			id: 'SEN-2045',
			tenantId: 'harbourline',
			title: 'Unexpected mailbox forwarding rule',
			category: 'Email security',
			asset: 'M365 / finance@demo.invalid',
			severity: 'High',
			status: 'Escalated',
			time: '11:41',
			description: 'A forwarding rule to an unfamiliar recipient was added in a demonstration mailbox. The change would require owner verification.',
			confidence: 89,
			indicators: ['New external forwarding target', 'Mailbox rule modified', 'Owner confirmation outstanding'],
			timeline: ['11:39 · Rule created', '11:41 · Audit event detected', '11:44 · Human review requested']
		},
		{
			id: 'SEN-2044',
			tenantId: 'harbourline',
			title: 'New privileged group membership',
			category: 'Identity & access',
			asset: 'ENTRA-DEMO',
			severity: 'Medium',
			status: 'Awaiting review',
			time: '10:26',
			description: 'A test identity was added to an elevated permission group. No malicious activity is established; verify change approval.',
			confidence: 78,
			indicators: ['Role membership changed', 'No change ticket linked', 'Demo environment'],
			timeline: ['10:24 · Role assignment', '10:26 · Alert generated', '10:27 · Review queued']
		},
		{
			id: 'SEN-2043',
			tenantId: 'summit',
			title: 'Endpoint security agent heartbeat delay',
			category: 'Agent health',
			asset: 'LNX-DEMO-03',
			severity: 'Low',
			status: 'Contained',
			time: '09:12',
			description: 'A sample endpoint failed to report its expected heartbeat; telemetry resumed in the simulated timeline.',
			confidence: 99,
			indicators: ['7-minute reporting gap', 'Heartbeat restored', 'No threat evidence'],
			timeline: ['09:05 · Heartbeat missed', '09:12 · Monitoring health alert', '09:14 · Agent reconnected']
		}
	];
	const severities: (Severity | 'All')[] = ['All', 'Critical', 'High', 'Medium', 'Low'];
	const nav: { name: View; short: string; description: string }[] = [
		{ name: 'Overview', short: 'OV', description: 'Command centre' },
		{ name: 'Customers', short: 'CU', description: 'SaaS customer portfolio' },
		{ name: 'Incidents', short: 'IN', description: 'Detection queue' },
		{ name: 'AI Analyst', short: 'AI', description: 'Investigative intelligence' },
		{ name: 'Response Centre', short: 'RC', description: 'Review and response' },
		{ name: 'Detection Engineering', short: 'DE', description: 'Rules and coverage' },
		{ name: 'Event Pipeline', short: 'EP', description: 'Synthetic event correlation' },
		{ name: 'Security Architecture', short: 'SA', description: 'SaaS access and policy' },
		{ name: 'API Lab', short: 'LB', description: 'Local backend integration' },
		{ name: 'Assets', short: 'AS', description: 'Environment coverage' },
		{ name: 'Reports', short: 'RP', description: 'Security intelligence' }
	];
	const dailyNav = nav.filter((item) => getGuide(item.name).category === 'daily');
	const advancedNav = nav.filter((item) => getGuide(item.name).category === 'advanced');
	const assets = [
		{ name: 'WIN-DEMO-07', type: 'Windows workstation', agent: 'Connected', risk: 'Elevated', group: 'Endpoints' },
		{ name: 'LNX-DEMO-03', type: 'Linux server', agent: 'Connected', risk: 'Low', group: 'Servers' },
		{ name: 'FW-EDGE-DEMO-01', type: 'Network firewall', agent: 'Connected', risk: 'Low', group: 'Network' },
		{ name: 'ENTRA-DEMO', type: 'Cloud identity', agent: 'Connected', risk: 'Moderate', group: 'Cloud' },
		{ name: 'M365-DEMO', type: 'Microsoft 365 tenant', agent: 'Connected', risk: 'Elevated', group: 'Cloud' },
		{ name: 'WIN-DEMO-11', type: 'Windows workstation', agent: 'Paused', risk: 'Unknown', group: 'Endpoints' }
	];
	const hourly = [
		{ hour: '08', count: 15 }, { hour: '09', count: 24 }, { hour: '10', count: 17 },
		{ hour: '11', count: 32 }, { hour: '12', count: 19 }, { hour: '13', count: 37 },
		{ hour: '14', count: 45 }, { hour: '15', count: 26 }, { hour: '16', count: 34 },
		{ hour: '17', count: 23 }, { hour: '18', count: 41 }, { hour: '19', count: 29 }
	];
	let view: View = 'Overview';
	let incidents = [...seed];
	let filter: Severity | 'All' = 'All';
	let search = '';
	let selectedId = seed[0].id;
	let demoCount = 0;
	let analysed: Record<string, boolean> = {};
	let decisions: Record<string, 'Reviewed — proposed' | 'Rejected — no action'> = {};
	let briefingGenerated = false;
	let menuOpen = false;
	let advancedOpen = false;
	let incidentDataMode: 'simulated' | 'local' = 'simulated';
	let localTenantId = '';
	let localCaseId = '';
	let labSession: { user: string; csrf: string } | null = null;
	$: visibleIncidents = incidents.filter((incident) => {
		const matchesSeverity = filter === 'All' || incident.severity === filter;
		const term = search.trim().toLowerCase();
		return matchesSeverity && (!term || [incident.id, incident.title, incident.asset, incident.category].join(' ').toLowerCase().includes(term));
	});
	$: selected = incidents.find((item) => item.id === selectedId) ?? incidents[0];
	$: openCases = incidents.filter((i) => i.status !== 'Contained').length;
	$: criticalCases = incidents.filter((i) => i.severity === 'Critical').length;
	$: highCases = incidents.filter((i) => i.severity === 'High').length;
	function selectView(next: View) {
		view = next;
		if (getGuide(next).category === 'advanced') advancedOpen = true;
		menuOpen = false;
	}
	function handleLabSessionChange(next: { user: string; csrf: string } | null) {
		labSession = next;
	}
	function openPipelineCase(tenantId: string, caseId: string) {
		localTenantId = tenantId;
		localCaseId = caseId;
		incidentDataMode = 'local';
		selectView('Incidents');
	}
	function openLocalApiLab() {
		selectView('API Lab');
	}
	function openCompanionLocalWorkspace(tenant: string, caseId: string) {
		localTenantId = tenant;
		localCaseId = caseId;
		incidentDataMode = 'local';
		selectView(view === 'Incidents' ? 'AI Analyst' : 'Incidents');
	}
	function openLinkedDetectionIncident(id: string) {
		incidentDataMode = 'simulated';
		selectedId = id;
		filter = 'All';
		search = '';
		selectView('Incidents');
	}
	function openInvestigation(id: string) {
		incidentDataMode = 'simulated';
		selectedId = id;
		selectView('AI Analyst');
	}
	function injectAlert() {
		incidentDataMode = 'simulated';
		demoCount += 1;
		const item: Incident = {
			id: 'SEN-LAB-' + String(demoCount).padStart(3, '0'),
			tenantId: 'alderwick',
			title: 'Simulated unusual DNS activity',
			category: 'Network defence',
			asset: 'LNX-DEMO-03',
			severity: 'High',
			status: 'Awaiting review',
			time: 'DEMO',
			description: 'Synthetic DNS activity was generated only in this browser. No alert was sent to a real SOC, and no endpoint was contacted.',
			confidence: 72,
			indicators: ['Synthetic DNS query pattern', 'Illustrative enrichment only', 'No live telemetry'],
			timeline: ['DEMO · Synthetic event created in browser', 'DEMO · Example detection matched', 'DEMO · Awaiting hypothetical analyst review']
		};
		incidents = [item, ...incidents];
		selectedId = item.id;
		filter = 'All';
		search = '';
		view = 'Incidents';
	}
	// Keep the local RH Sentry demo address clean if a referrer app appended
	// attribution parameters. This changes only the URL, not app or session state.
	onMount(() => {
		const cleanPath = canonicalSentryPreviewPath(new URL(window.location.href));
		if (cleanPath !== null) {
			window.history.replaceState(window.history.state, '', cleanPath);
		}
	});

	function resetDemo() {
		incidentDataMode = 'simulated';
		incidents = [...seed];
		demoCount = 0;
		selectedId = seed[0].id;
		search = '';
		filter = 'All';
		briefingGenerated = false;
		analysed = {};
		decisions = {};
		view = 'Overview';
	}
</script>

<svelte:head>
	<title>RH Sentry — Command Centre (Demo)</title>
	<meta name="description" content="Local, simulated RH Sentry security operations interface. No live monitoring or automated response." />
</svelte:head>

<div class="sentry-shell">
	<aside class={"sidebar" + (menuOpen ? " mobile-open" : "")} aria-label="RH Sentry sections">
		<div class="sidebar-brand">
			<div class="brand-overline">RED HORIZON CYBER GROUP</div>
			<div class="brand-name"><span class="brand-rh"><span class="brand-r">R</span><span class="brand-h">H</span></span> <span class="brand-word">SENTRY</span><span class="brand-dot">.</span></div>
			<div class="brand-subtitle">SECURITY OPERATIONS PLATFORM</div>
		</div>
		<div class="sidebar-section-label">CORE WORK</div>
		<nav class="sidebar-nav" aria-label="Core navigation">
			{#each dailyNav as item}
				<button type="button" class:active={view === item.name} aria-current={view === item.name ? 'page' : undefined} on:click={() => selectView(item.name)}>
					<span class="nav-icon" aria-hidden="true">{item.short}</span>
					<span class="nav-copy"><strong>{item.name === 'Overview' ? 'Command Centre' : item.name}</strong><small>{item.description}</small></span>
					<span class="nav-caret" aria-hidden="true">›</span>
				</button>
			{/each}
		</nav>
		<button type="button" class="advanced-toggle" aria-expanded={advancedOpen}
			on:click={() => (advancedOpen = !advancedOpen)}>
			{advancedOpen ? '−' : '+'} Advanced tools <span aria-hidden="true">{advancedOpen ? '⌃' : '⌄'}</span>
		</button>
		{#if advancedOpen}
			<nav class="sidebar-nav" aria-label="Advanced tools navigation">
				{#each advancedNav as item}
					<button type="button" class:active={view === item.name} aria-current={view === item.name ? 'page' : undefined} on:click={() => selectView(item.name)}>
						<span class="nav-icon" aria-hidden="true">{item.short}</span>
						<span class="nav-copy"><strong>{item.name}</strong><small>{item.description}</small></span>
						<span class="nav-caret" aria-hidden="true">›</span>
					</button>
				{/each}
			</nav>
		{/if}
		<div class="sidebar-bottom">
			<div class="sidebar-status"><span class="status-dot amber"></span><div><strong>Development workspace</strong><small>No sensors connected</small></div></div>
			<div class="sidebar-footer">RH SENTRY <span>/</span> BUILD 0.1 PREVIEW</div>
		</div>
	</aside>

	<div class="workarea">
		<div class="demo-banner">
			<span class="demo-pill">DEMO ENVIRONMENT</span>
			<span>All organisations and incidents are fictional. The optional local API uses SQLite; no live SOC telemetry is connected.</span>
			<button type="button" on:click={resetDemo} class="reset-demo">Reset visual demo ↺</button>
		</div>

		<header class="topbar">
			<div class="topbar-left">
				<button class="mobile-menu" type="button" aria-label="Toggle navigation" on:click={() => (menuOpen = !menuOpen)}>☰</button>
				<div class="breadcrumbs">PLATFORM <span>/</span> <strong>{view === 'Overview' ? 'COMMAND CENTRE' : view.toUpperCase()}</strong></div>
			</div>
			<div class="topbar-actions">
				<PlatformGuide currentView={view} onNavigate={selectView} />
				<div class="signal-tag"><span class="status-dot amber"></span> DATA SOURCE: {((view === 'Overview' || view === 'Incidents' || view === 'AI Analyst' || view === 'Assets' || view === 'Detection Engineering' || view === 'Response Centre') && incidentDataMode === 'local') || view === 'Event Pipeline' ? 'LOCAL SQLITE LAB · SYNTHETIC' : 'SIMULATED'}</div>
				<div class="avatar" aria-label="Demonstration operator">RH</div>
			</div>
		</header>

		<main>
			<div class="page-heading">
				<div>
					<div class="eyebrow">RED HORIZON / DEFENSIVE INTELLIGENCE</div>
					<h1>{view === 'Overview' ? 'Command Centre' : view}</h1>
					<p>{view === 'Overview' ? 'A single view of the signals that matter. Investigate with context. Respond with control.' : view === 'Incidents' ? 'Prioritised investigations and evidence-first incident management.' : view === 'Customers' ? 'Manage customer context, scoped incident views and the future SaaS experience.' : view === 'AI Analyst' ? 'Intelligence that explains its reasoning and keeps analysts in control.' : view === 'Response Centre' ? 'Review proposed defensive actions, control approvals and explore sample response playbooks.' : view === 'Detection Engineering' ? 'Explore example detection rules, validate synthetic events and understand monitoring blind spots.' : view === 'Event Pipeline' ? 'Generate fictional telemetry, inspect provenance and review explainable lab correlations.' : view === 'Security Architecture' ? 'Design customer boundaries, least-privilege access and human response approval policies.' : view === 'API Lab' ? 'Explore the isolated localhost API with fictional customer identities, persistent records and server-side tenant checks.' : view === 'Assets' ? 'A clear view of the systems your future SOC will protect.' : 'Decision-ready intelligence for security leaders and clients.'}</p>
				</div>
				<div class="heading-actions">
					<button type="button" class="button-secondary" on:click={() => selectView(getGuide(view).next ?? 'Overview')}>
						Next: {getGuide(view).nextLabel} <span>↗</span>
					</button>
					{#if view === 'Overview' && incidentDataMode === 'simulated'}
						<button type="button" class="button-primary" on:click={injectAlert}>+ Inject demo alert</button>
					{/if}
				</div>
			</div>

			{#if view === 'Overview' || view === 'Incidents' || view === 'AI Analyst' || view === 'Assets' || view === 'Detection Engineering' || view === 'Response Centre'}
				<div class="data-source-selector" aria-label="Incident data source">
					<div>
						<strong>Workspace data source</strong>
						<p>{incidentDataMode === 'simulated' ? 'Interactive fictional records and hypothetical monitoring/AI displays.' : 'Authenticated fictional customer records from the local SQLite API. No live monitoring or AI engine is connected.'}</p>
					</div>
					<div class="data-source-buttons">
						<button type="button" class:chosen={incidentDataMode === 'simulated'} aria-pressed={incidentDataMode === 'simulated'} on:click={() => (incidentDataMode = 'simulated')}>Simulation</button>
						<button type="button" class:chosen={incidentDataMode === 'local'} aria-pressed={incidentDataMode === 'local'} on:click={() => (incidentDataMode = 'local')}>Local API / SQLite</button>
					</div>
				</div>
			{/if}

			{#if view === 'Overview' && incidentDataMode === 'simulated'}
				<div class="health-strip">
					<div class="health-mark"><span class="health-orbit"></span><span class="health-centre"></span></div>
					<div class="health-copy">
						<div class="health-headline">Visibility starts here.</div>
						<div class="health-desc">This is an interactive design prototype. Live data ingestion, detection rules and AI reasoning are not connected.</div>
					</div>
					<span class="health-badge">LAB PREVIEW · OFFLINE</span>
				</div>

				<section class="metric-grid" aria-label="Simulated metrics">
					<div class="metric"><div class="metric-label">OPEN INVESTIGATIONS <span>↗</span></div><div class="metric-value">{openCases.toString().padStart(2, '0')}<span class="metric-inline">cases</span></div><div class="metric-foot">Demonstration incident queue</div></div>
					<div class="metric"><div class="metric-label">CRITICAL THREATS <span>!</span></div><div class="metric-value red">{criticalCases.toString().padStart(2, '0')}<span class="metric-inline">flagged</span></div><div class="metric-foot">Requires analyst prioritisation</div></div>
					<div class="metric"><div class="metric-label">HIGH-SEVERITY CASES <span>◆</span></div><div class="metric-value">{highCases.toString().padStart(2, '0')}<span class="metric-inline">alerts</span></div><div class="metric-foot">Synthetic prioritisation results</div></div>
					<div class="metric"><div class="metric-label">MONITORED ASSETS <span>◉</span></div><div class="metric-value">00<span class="metric-inline">live</span></div><div class="metric-foot"><span class="mini-dot amber"></span> 6 sample assets in demo</div></div>
				</section>

				<div class="coverage-quicklink">
					<div><span class="coverage-key">DETECTION & MONITORING</span><strong>Coverage design needs connected sources</strong><p>Six example rules are ready to explore, but zero detection rules or telemetry sources are live.</p></div>
					<button type="button" on:click={() => selectView('Detection Engineering')}>Explore detection engineering ↗</button>
				</div>

				<div class="dashboard-grid">
					<section class="panel signals-panel">
						<div class="panel-head">
							<div><div class="panel-kicker">SIGNAL INTELLIGENCE</div><h2>Security activity</h2></div>
							<div class="subtle-label">12 SAMPLE INTERVALS</div>
						</div>
						<div class="chart-legend"><span class="legend-red"></span> Illustrative event volume <span class="chart-note">Not live telemetry</span></div>
						<div class="chart-area">
							<div class="chart-ylabels"><span>50</span><span>40</span><span>30</span><span>20</span><span>10</span><span>0</span></div>
							<div class="chart-bars">
								{#each hourly as bar}
									<div class="bar-column" title={'Illustrative events: ' + bar.count}>
										<div class="bar-track"><div class="bar-fill" style:height={(bar.count / 50 * 100) + '%'}></div></div>
										<span>{bar.hour}:00</span>
									</div>
								{/each}
							</div>
						</div>
					</section>
					<section class="panel posture-panel">
						<div class="panel-head"><div><div class="panel-kicker">ENVIRONMENT POSTURE</div><h2>Coverage preview</h2></div></div>
						<div class="radial-wrap"><div class="coverage-ring"><div class="coverage-ring-inner"><strong>0%</strong><span>LIVE COVERAGE</span></div></div></div>
						<div class="posture-rows">
							<div><span><i class="mini-dot green"></i> Sample assets</span><strong>6 configured</strong></div>
							<div><span><i class="mini-dot amber"></i> Connected sensors</span><strong>0 real</strong></div>
							<div><span><i class="mini-dot red-dot"></i> Response actions</span><strong>Disabled</strong></div>
						</div>
					</section>
				</div>
			{/if}

			{#if view === 'Overview' && incidentDataMode === 'local'}
				<LocalCommandCentre bind:selectedTenantId={localTenantId} onOpenApiLab={openLocalApiLab}
					onOpenCase={openPipelineCase} onOpenPipeline={() => selectView('Event Pipeline')}/>
			{/if}

			{#if (view === 'Overview' || view === 'Incidents') && incidentDataMode === 'simulated'}
				<div class="section-title-row">
					<div><div class="eyebrow">TRIAGE AND RESPONSE</div><h2>{view === 'Overview' ? 'Priority investigations' : 'Incident queue'}</h2></div>
					<span class="section-number">{visibleIncidents.length} DISPLAYED / {incidents.length} TOTAL</span>
				</div>
				<div class="incident-layout">
					<section class="panel incident-list">
						<div class="list-toolbar">
							<label class="search-wrapper"><span class="sr-only">Search demonstration incidents</span><span aria-hidden="true">⌕</span><input type="search" bind:value={search} placeholder="Search investigations, assets..." /></label>
							<div class="filters" aria-label="Filter by severity">
								{#each severities as category}
									<button type="button" class={filter === category ? "filter-active" : ""} aria-pressed={filter === category} on:click={() => (filter = category)}>{category}</button>
								{/each}
							</div>
						</div>
						<div class="table-head"><span>INCIDENT</span><span>SEVERITY</span><span>STATE</span><span>TIME</span></div>
						<div class="case-rows">
							{#each visibleIncidents as incident}
								<button type="button" class={"case-row" + (selectedId === incident.id ? " selected-case" : "")} on:click={() => (selectedId = incident.id)}>
									<div class="case-name"><div class="incident-title">{incident.title}</div><div class="incident-meta">{incident.id} <span>·</span> {incident.asset}</div></div>
									<div><span class="severity" class:critical={incident.severity === 'Critical'} class:high={incident.severity === 'High'} class:medium={incident.severity === 'Medium'}>{incident.severity}</span></div>
									<div class="state-text">{incident.status}</div>
									<div class="time-text">{incident.time}</div>
								</button>
							{:else}
								<div class="empty">No demonstration incidents match that search. Clear the filters to see the sample cases.</div>
							{/each}
						</div>
						<div class="list-foot">SYNTHETIC DATASET <span>·</span> SELECT A ROW TO INSPECT</div>
					</section>
					<section class="panel detail-panel">
						<div class="panel-head">
							<div><div class="panel-kicker">SELECTED INVESTIGATION</div><h2>{selected.id}</h2></div>
							<span class="mock-badge">SIMULATED</span>
						</div>
						<div class="detail-title">{selected.title}</div>
						<div class="detail-context">{selected.category} <span>·</span> {selected.asset}</div>
						<div class="divider"></div>
						<div class="detail-meta"><span>SEVERITY</span><strong>{selected.severity}</strong></div>
						<div class="detail-meta"><span>WORKFLOW STATE</span><strong>{selected.status}</strong></div>
						<div class="detail-meta"><span>EXAMPLE AI CONFIDENCE</span><strong>{selected.confidence}%*</strong></div>
						<div class="divider"></div>
						<div class="detail-subheading">Analyst brief</div>
						<p class="detail-description">{selected.description}</p>
						<div class="detail-subheading">Observed indicators</div>
						<ul class="indicator-list">{#each selected.indicators as indicator}<li>{indicator}</li>{/each}</ul>
						<button type="button" class="detail-link" on:click={() => selectView('AI Analyst')}>Open investigation workspace <span>↗</span></button>
						<p class="footnote">*Illustrative value only; not produced by a model.</p>
					</section>
				</div>
			{/if}

			{#if view === 'Customers'}
				<CustomerPortfolio {incidents} />
			{/if}

			{#if view === 'AI Analyst' && incidentDataMode === 'simulated'}
				<AnalystWorkspace {incidents} bind:selectedId bind:analysed bind:decisions />
			{/if}

			{#if view === 'Incidents' && incidentDataMode === 'local'}
				<LocalCaseWorkspace mode="incidents" bind:selectedTenantId={localTenantId} bind:selectedCaseId={localCaseId}
					csrf={labSession?.csrf ?? ''} labSessionUser={labSession?.user ?? ''}
					onOpenApiLab={openLocalApiLab} onSwitchWorkspace={openCompanionLocalWorkspace}/>
			{/if}

			{#if view === 'AI Analyst' && incidentDataMode === 'local'}
				<LocalCaseWorkspace mode="analyst" bind:selectedTenantId={localTenantId} bind:selectedCaseId={localCaseId}
					csrf={labSession?.csrf ?? ''} labSessionUser={labSession?.user ?? ''}
					onOpenApiLab={openLocalApiLab} onSwitchWorkspace={openCompanionLocalWorkspace}/>
			{/if}

			{#if view === 'Response Centre' && incidentDataMode === 'simulated'}
				<ResponseCentre {incidents} {analysed} bind:decisions bind:selectedId onInvestigate={openInvestigation} />
			{/if}
			{#if view === 'Response Centre' && incidentDataMode === 'local'}
				<LocalResponseCentre bind:selectedTenantId={localTenantId}
					csrf={labSession?.csrf ?? ''} labSessionUser={labSession?.user ?? ''}
					onOpenApiLab={openLocalApiLab} onOpenCase={openPipelineCase}/>
			{/if}

			{#if view === 'Detection Engineering' && incidentDataMode === 'simulated'}
				<DetectionEngineering onOpenIncident={openLinkedDetectionIncident} />
			{/if}
			{#if view === 'Detection Engineering' && incidentDataMode === 'local'}
				<LocalDetectionEngineering bind:selectedTenantId={localTenantId}
					csrf={labSession?.csrf ?? ''} labSessionUser={labSession?.user ?? ''}
					onOpenApiLab={openLocalApiLab} onOpenPipeline={() => selectView('Event Pipeline')}/>
			{/if}

			{#if view === 'Security Architecture'}
				<PlatformSecurity />
			{/if}

			{#if view === 'Event Pipeline'}
				<SyntheticEventPipeline csrf={labSession?.csrf ?? ''} labSessionUser={labSession?.user ?? ''}
					onOpenApiLab={openLocalApiLab} onOpenCase={openPipelineCase} />
			{/if}

			{#if view === 'API Lab'}
				<ApiLab sharedSession={labSession} onSessionChange={handleLabSessionChange} />
			{/if}

			{#if view === 'Assets' && incidentDataMode === 'simulated'}
				<section class="panel assets-panel"><div class="panel-head"><div><div class="panel-kicker">ENVIRONMENT / DEMONSTRATION</div><h2>Asset inventory</h2></div><span class="mock-badge">6 SAMPLE ASSETS</span></div><div class="assets-grid">{#each assets as asset}<div class="asset-card"><div class="asset-top"><strong>{asset.name}</strong><span class:offline={asset.agent === 'Paused'} class="asset-indicator">{asset.agent}</span></div><div class="asset-type">{asset.type}</div><div class="asset-bottom"><span>{asset.group}</span><span>Example risk: {asset.risk}</span></div></div>{/each}</div><p class="footnote">All assets are fictional. No agents have been installed from this page.</p></section>
			{/if}

			{#if view === 'Assets' && incidentDataMode === 'local'}
				<LocalAssets bind:selectedTenantId={localTenantId} csrf={labSession?.csrf ?? ''}
					labSessionUser={labSession?.user ?? ''} onOpenApiLab={openLocalApiLab}
					onOpenCase={openPipelineCase}/>
			{/if}

			{#if view === 'Reports'}
				<div class="workspace-grid">
					<section class="panel report-card"><div class="panel-head"><div><div class="panel-kicker">EXECUTIVE INTELLIGENCE</div><h2>Security posture briefing</h2></div><span class="mock-badge">DEMO ONLY</span></div><p>Generate a local demonstration briefing from the sample incident queue. No file is exported and no customer information is processed.</p><div class="report-stats"><div><strong>{incidents.length}</strong><span>Sample incidents</span></div><div><strong>{openCases}</strong><span>Open cases</span></div><div><strong>0</strong><span>Live sensors</span></div></div><button type="button" class="button-primary" on:click={() => (briefingGenerated = true)}>Generate sample briefing</button>{#if briefingGenerated}<div class="report-output" role="status"><div class="message-label">SAMPLE BRIEFING GENERATED</div><p>The demonstration environment contains {incidents.length} synthetic cases, including {criticalCases} critical and {highCases} high-priority items. No live exposure assessment or security assurance can be inferred from this data.</p></div>{/if}</section>
					<section class="panel timeline-card"><div class="panel-head"><div><div class="panel-kicker">REPORTING ROADMAP</div><h2>Planned exports</h2></div></div><ul class="roadmap"><li>Executive monthly security summary</li><li>Incident lifecycle and response evidence</li><li>Asset exposure and control coverage</li><li>Detection efficacy and data quality</li></ul><p class="footnote">These are proposed product features, not implemented export functionality.</p></section>
				</div>
			{/if}
			<footer class="product-footer"><span>RH SENTRY / RED HORIZON CYBER GROUP</span><span>INTERACTIVE FRONTEND PROTOTYPE · NO LIVE PROTECTION</span></footer>
		</main>
	</div>
</div>

<style>
	.sentry-shell, .sentry-shell button, .sentry-shell input { font-family: Inter, 'Segoe UI', Arial, sans-serif; }
	.sentry-shell :global(*) { box-sizing: border-box; }
	.sentry-shell { --ink: #edf1f7; --muted: #8994a5; --accent: #e33247; --line: #242c39; --panel: #111823; display: flex; min-height: 100vh; background: #090d14; color: var(--ink); font-size: 14px; }
	.sentry-shell button { cursor: pointer; }
	.sentry-shell button:focus-visible, .sentry-shell input:focus-visible { outline: 2px solid #f06a77; outline-offset: 3px; }
	.sidebar { width: 260px; flex: 0 0 260px; min-height: 0; border-right: 1px solid #202633; background: #0c111a; padding: 32px 17px 20px; display: flex; flex-direction: column; position: sticky; top: 0; align-self: flex-start; height: 100vh; height: 100dvh; overflow-y: auto; overflow-x: hidden; overscroll-behavior-y: contain; scrollbar-width: thin; scrollbar-color: #394455 #0c111a; }
	.sidebar-brand { padding: 4px 10px 52px; }
	.brand-overline { color: #858f9f; font-size: 9px; font-weight: 800; letter-spacing: .19em; margin-bottom: 14px; }
	.brand-name { font-size: 28px; font-weight: 850; letter-spacing: -.065em; line-height: 1; color: #f8f9fc; white-space: nowrap; }
	.brand-name .brand-rh { display: inline-flex; align-items: baseline; font: inherit; line-height: inherit; letter-spacing: inherit; vertical-align: baseline; }
	.brand-name .brand-rh > span { display: inline-block; font-family: inherit; font-size: 1em; font-weight: inherit; font-style: inherit; line-height: inherit; letter-spacing: inherit; vertical-align: baseline; }
	/* The red R appears optically smaller at sidebar sizes even with matching type metrics. Compensate visibly, without changing the white H or wordmark layout. */
	.brand-name .brand-r { color: #e33247; transform: scale(1.09); transform-origin: center center; }
	.brand-name .brand-h { color: #f8f9fc; }
	.brand-name .brand-word { color: #f8f9fc; font-weight: 500; letter-spacing: .04em; }
	.brand-name .brand-dot { color: #e33247; letter-spacing: 0; }
	.brand-subtitle { font-size: 9px; font-weight: 700; letter-spacing: .13em; color: #9da7b5; margin-top: 11px; }
	.sidebar-section-label { font-size: 10px; color: #677386; letter-spacing: .16em; font-weight: 800; padding: 0 15px 17px; }
	.advanced-toggle { display:flex; justify-content:space-between; align-items:center; width:100%; color:#a5b6c9; background:transparent; border:1px solid #2e3c4d; border-radius:7px; padding:12px 13px; cursor:pointer; font-size:11px; font-weight:750; margin:13px 0; }
	.advanced-toggle:hover {color:#edf3fa; border-color:#755163; }
	.advanced-toggle span { color:#d4788e; }

	.sidebar-nav { display: flex; flex-direction: column; gap: 5px; flex-shrink: 0; }
	.sidebar-nav button { border: 1px solid transparent; text-align: left; border-radius: 9px; display: flex; align-items: center; gap: 12px; padding: 13px 11px; background: transparent; color: #8f9cac; transition: background .2s, border-color .2s; width: 100%; }
	.sidebar-nav button:hover { background: #18202d; }
	.sidebar-nav button.active { color: white; border-color: #502736; background: linear-gradient(95deg, #3a1925 0%, #1a1924 100%); }
	.nav-icon { border: 1px solid #394251; background: #141c29; border-radius: 6px; width: 32px; height: 32px; flex-shrink: 0; display: grid; place-items: center; font-size: 10px; font-weight: 800; letter-spacing: -.02em; }
	.active .nav-icon { border-color: #e33247; color: #ff6172; background: #411d2a; }
	.nav-copy { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
	.nav-copy strong { font-size: 12px; font-weight: 750; }
	.nav-copy small { font-size: 10px; color: #707e90; white-space: nowrap; }
	.active .nav-copy small { color: #cf9fac; }
	.nav-caret { margin-left: auto; color: #607083; }
	.sidebar-bottom { margin-top: auto; }
	.sidebar-status { border: 1px solid #30313b; border-radius: 9px; background: #141922; padding: 12px; display: flex; gap: 10px; align-items: center; }
	.sidebar-status div { display: flex; flex-direction: column; gap: 3px; }
	.sidebar-status strong { font-size: 11px; font-weight: 650; }
	.sidebar-status small { color: #8b95a4; font-size: 10px; }
	.status-dot, .mini-dot { display: inline-block; background: #22bd85; border-radius: 50%; width: 7px; height: 7px; flex-shrink: 0; }
	.status-dot.amber, .mini-dot.amber { background: #dfaa5e; }
	.mini-dot.red-dot { background: #e84b5c; }
	.mini-dot.green { background: #51c49a; }
	.sidebar-footer { margin-top: 23px; font-size: 9px; font-weight: 700; letter-spacing: .12em; color: #737f8e; }
	.sidebar-footer span { color: #e64a5d; padding: 0 7px; }
	.workarea { flex: 1; min-width: 0; }
	.demo-banner { display: flex; gap: 12px; align-items: center; padding: 9px 40px; background: #201b20; color: #d1aab0; font-size: 11px; border-bottom: 1px solid #513039; }
	.demo-pill { font-size: 9px; font-weight: 800; border: 1px solid #ae4f5b; color: #ffc7cc; padding: 5px 8px; border-radius: 4px; letter-spacing: .09em; white-space: nowrap; }
	.reset-demo { margin-left: auto; border: 0; background: none; color: #f7b3be; font-size: 11px; white-space: nowrap; }
	.reset-demo:hover { color: white; }
	.topbar { display: flex; justify-content: space-between; align-items: center; padding: 18px 40px; border-bottom: 1px solid #1f2632; min-height: 72px; }
	.topbar-left, .topbar-actions { display: flex; align-items: center; gap: 18px; }
	.breadcrumbs { font-size: 10px; color: #707e90; font-weight: 800; letter-spacing: .12em; }
	.breadcrumbs span { padding: 0 13px; color: #e33247; }
	.breadcrumbs strong { color: #c9d2df; font-weight: 700; }
	.signal-tag { color: #9ca7b6; font-size: 10px; letter-spacing: .06em; display: flex; gap: 9px; align-items: center; }
	.avatar { background: #3d2330; color: #ffdbe0; border: 1px solid #704350; border-radius: 8px; width: 34px; height: 34px; display: grid; place-items: center; font-size: 11px; font-weight: 800; }
	.mobile-menu { display: none; color: #fff; border: 1px solid #3a4350; background: transparent; border-radius: 6px; padding: 6px 10px; }
	main { padding: 38px 40px 25px; max-width: 1750px; margin: 0 auto; background-image: radial-gradient(circle at 95% 0%, rgba(185,31,51,.045), transparent 34%); }
	.page-heading { display: flex; justify-content: space-between; gap: 25px; align-items: flex-end; margin-bottom: 28px; }
	.eyebrow, .panel-kicker { color: #d34b5c; letter-spacing: .18em; font-weight: 800; font-size: 10px; }
	h1 { font-size: clamp(28px, 3.1vw, 39px); font-weight: 760; letter-spacing: -.04em; margin: 10px 0 9px; line-height: 1.2; }
	.page-heading p { color: #8c99ab; font-size: 13px; margin: 0; max-width: 650px; line-height: 1.65; }
	.heading-actions { display: flex; gap: 10px; flex-shrink: 0; }
	.button-primary, .button-secondary { padding: 12px 16px; border-radius: 7px; font-size: 11px; font-weight: 800; letter-spacing: .02em; white-space: nowrap; }
	.button-primary { background: #d92c42; border: 1px solid #df495d; color: #fff; }
	.button-primary:hover { background: #f1435a; }
	.button-secondary { color: #c9d5e2; background: #151d29; border: 1px solid #2c3645; }
	.button-secondary:hover { background: #222c39; }
	.button-secondary span { color: #e04a5d; margin-left: 10px; }
	.health-strip { border: 1px solid #30323c; background: linear-gradient(105deg,#1d202b,#141a25 60%,#141a23); border-radius: 11px; display: flex; align-items: center; padding: 19px 23px; gap: 20px; margin-bottom: 23px; }
	.health-mark { border: 1px solid #935b4d; width: 46px; height: 46px; border-radius: 50%; flex-shrink: 0; display: grid; place-items: center; position: relative; }
	.health-orbit { border: 1px dashed #c39273; width: 32px; height: 32px; border-radius: 50%; }
	.health-centre { width: 8px; height: 8px; border-radius: 50%; background: #e4b08a; position: absolute; }
	.health-headline { font-size: 15px; font-weight: 800; margin-bottom: 5px; }
	.health-desc { color: #95a1b3; font-size: 11px; line-height: 1.6; }
	.health-badge { font-size: 9px; letter-spacing: .1em; font-weight: 800; margin-left: auto; flex-shrink: 0; border: 1px solid #594b37; color: #f0bf73; padding: 8px 10px; border-radius: 5px; }
	.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 14px; margin-bottom: 22px; }
	.metric { background: #111823; border: 1px solid #252d3a; border-radius: 10px; padding: 20px 21px; min-width: 0; }
	.metric-label { font-size: 10px; letter-spacing: .11em; font-weight: 800; color: #8391a5; display: flex; justify-content: space-between; gap: 8px; }
	.metric-label span { color: #af5966; font-size: 15px; }
	.metric-value { font-size: 39px; font-weight: 760; letter-spacing: -.055em; line-height: 1.2; margin: 17px 0 10px; }
	.metric-value.red { color: #f05a6a; }
	.metric-inline { font-size: 11px; font-weight: 500; letter-spacing: normal; color: #8998a9; margin-left: 9px; }
	.metric-foot { font-size: 10px; color: #7f8d9e; display: flex; align-items: center; gap: 7px; }
	.dashboard-grid { display: grid; grid-template-columns: 1.8fr 1fr; gap: 16px; margin-bottom: 38px; }
	.panel { background: #111823; border: 1px solid #252e3b; border-radius: 11px; min-width: 0; overflow: hidden; }
	.signals-panel, .posture-panel, .analyst-card, .timeline-card, .report-card, .assets-panel { padding: 22px 24px; }
	.panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 13px; }
	.panel-kicker { font-size: 9px; color: #a25d6b; margin-bottom: 8px; }
	h2 { font-size: 18px; letter-spacing: -.025em; font-weight: 740; margin: 0; }
	.subtle-label { font-size: 9px; font-weight: 700; color: #69788d; letter-spacing: .08em; }
	.chart-legend { margin-top: 26px; color: #bbc6d3; display: flex; gap: 8px; font-size: 10px; align-items: center; }
	.legend-red { width: 7px; height: 7px; background: #df3c54; border-radius: 2px; }
	.chart-note { margin-left: auto; color: #6e7c90; }
	.chart-area { display: flex; height: 205px; margin-top: 15px; gap: 12px; }
	.chart-ylabels { display: flex; flex-direction: column; justify-content: space-between; color: #5e6b7e; font-size: 9px; padding-bottom: 24px; width: 15px; }
	.chart-bars { display: grid; grid-template-columns: repeat(12,minmax(0,1fr)); flex: 1; gap: 9px; align-items: end; background: repeating-linear-gradient(to top, #242e3a 0px,#242e3a 1px,transparent 1px,transparent 36px); }
	.bar-column { height: 100%; min-width: 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; }
	.bar-track { height: calc(100% - 28px); width: 100%; max-width: 28px; display: flex; align-items: end; }
	.bar-fill { width: 100%; background: linear-gradient(to top, #792438, #ed4156); border-radius: 3px 3px 0 0; opacity: .88; transition: height .25s; }
	.bar-column span { font-size: 9px; color: #6e7b8c; height: 24px; padding-top: 8px; }
	.radial-wrap { display: flex; justify-content: center; padding: 16px 0; }
	.coverage-ring { width: 174px; height: 174px; border-radius: 50%; background: conic-gradient(#df3c54 0deg 0deg, #27313e 0deg 360deg); padding: 15px; }
	.coverage-ring-inner { width: 100%; height: 100%; border-radius: 50%; background: #111823; display: flex; flex-direction: column; justify-content: center; align-items: center; }
	.ring-inner strong { font-size: 39px; font-weight: 750; letter-spacing: -.06em; }
	.ring-inner span { font-size: 9px; font-weight: 800; color: #768598; letter-spacing: .12em; margin-top: 3px; }
	.posture-rows { display: flex; flex-direction: column; gap: 12px; padding-top: 6px; }
	.posture-rows div { display: flex; justify-content: space-between; gap: 8px; color: #8997a8; font-size: 11px; }
	.posture-rows div span { display: flex; gap: 8px; align-items: center; }
	.posture-rows strong { color: #cbd4df; font-weight: 650; }
	.section-title-row { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 16px; }
	.section-title-row .eyebrow { margin-bottom: 8px; }
	.section-number { color: #758295; font-size: 9px; letter-spacing: .12em; font-weight: 800; }
	.incident-layout { display: grid; grid-template-columns: minmax(0,1.85fr) minmax(280px,1fr); gap: 16px; align-items: start; }
	.list-toolbar { padding: 15px 16px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #262f3b; justify-content: space-between; }
	.search-wrapper { display: flex; align-items: center; gap: 7px; background: #0b111a; border: 1px solid #313b49; border-radius: 6px; padding: 8px 10px; color: #99a6b7; min-width: 195px; flex: 1; max-width: 350px; }
	.search-wrapper > span { font-size: 19px; line-height: 12px; }
	.search-wrapper input { outline: 0; border: 0; background: none; color: #e0e7ef; font-size: 11px; width: 100%; }
	.search-wrapper input::placeholder { color: #667489; }
	.filters { display: flex; flex-wrap: wrap; gap: 3px; }
	.filters button { background: transparent; border: 1px solid transparent; padding: 7px 9px; border-radius: 5px; font-size: 10px; color: #8492a3; }
	.filters button.filter-active { background: #3a2531; color: #ffb2bc; border-color: #62404a; }
	.table-head, .case-row { display: grid; grid-template-columns: minmax(170px, 2.2fr) 84px 104px 45px; gap: 12px; align-items: center; }
	.table-head { color: #758397; font-size: 9px; font-weight: 800; letter-spacing: .12em; padding: 13px 19px; background: #121b28; }
	.case-row { width: 100%; border: 0; border-top: 1px solid #232d3b; background: transparent; padding: 16px 19px; text-align: left; color: #ccd5e1; }
	.case-row:hover { background: #1a2534; }
	.case-row.selected-case { background: #1d222e; box-shadow: inset 3px 0 0 #e13b52; }
	.incident-title { font-size: 11px; font-weight: 700; color: #e3e9f1; line-height: 1.4; }
	.incident-meta { font-size: 10px; color: #758397; margin-top: 6px; overflow-wrap: anywhere; }
	.incident-meta span { color: #e34a5a; padding: 0 3px; }
	.severity { font-size: 10px; color: #a2b2c7; border-radius: 4px; background: #27313c; border: 1px solid #3d4754; padding: 5px 7px; }
	.severity.critical { color: #ff8798; background: #45232f; border-color: #793643; }
	.severity.high { color: #f6b274; background: #403126; border-color: #75543a; }
	.severity.medium { color: #b6adf8; background: #2d2c45; border-color: #4d4b70; }
	.state-text, .time-text { font-size: 10px; color: #9ba8b9; }
	.empty { padding: 30px; color: #9aabbf; font-size: 12px; }
	.list-foot { padding: 13px 19px; border-top: 1px solid #26303b; font-size: 9px; font-weight: 700; letter-spacing: .11em; color: #607287; }
	.list-foot span { color: #b44357; padding: 0 8px; }
	.detail-panel { padding: 23px; }
	.mock-badge { font-size: 9px; color: #e9a4af; background: #3a2330; border: 1px solid #704251; border-radius: 4px; padding: 7px 8px; font-weight: 800; letter-spacing: .06em; white-space: nowrap; }
	.detail-title { font-size: 16px; font-weight: 740; margin-top: 23px; line-height: 1.4; }
	.detail-context { font-size: 10px; color: #8899ab; margin-top: 8px; overflow-wrap: anywhere; }
	.detail-context span { color: #e64d61; padding: 0 5px; }
	.divider { height: 1px; background: #29313d; margin: 18px 0; }
	.detail-meta { display: flex; justify-content: space-between; gap: 8px; margin: 13px 0; }
	.detail-meta span { color: #77879a; font-size: 10px; letter-spacing: .03em; }
	.detail-meta strong { color: #d6e0e8; font-size: 11px; }
	.detail-subheading { font-size: 10px; font-weight: 800; color: #e6ebf0; margin-bottom: 10px; }
	.detail-description { color: #9dadbe; font-size: 11px; line-height: 1.85; margin: 0 0 19px; }
	.indicator-list { color: #9dabbc; font-size: 11px; padding-left: 18px; display: flex; flex-direction: column; gap: 10px; line-height: 1.5; }
	.indicator-list li::marker { color: #d44e60; }
	.detail-link { border: 1px solid #544050; background: #30202c; color: #f2b5bf; font-size: 11px; font-weight: 750; padding: 12px; border-radius: 6px; margin-top: 15px; width: 100%; }
	.detail-link:hover { background: #482635; }
	.detail-link span { margin-left: 5px; }
	.footnote { color: #778598; font-size: 10px; line-height: 1.7; margin: 16px 0 0; }
	.workspace-grid { display: grid; grid-template-columns: minmax(0,1.7fr) minmax(290px,1fr); gap: 16px; }
	.analyst-intro { display: flex; align-items: center; gap: 13px; padding: 25px 0; }
	.ai-glyph { font-size: 29px; color: #ef5367; border: 1px solid #743546; border-radius: 10px; background: #37212f; padding: 7px 13px; }
	.analyst-intro strong { font-size: 15px; }
	.analyst-intro p { color: #8b9aad; font-size: 11px; margin: 7px 0 0; }
	.analyst-message { background: #0c131d; border: 1px solid #2b3441; border-radius: 9px; padding: 21px; }
	.message-label { font-size: 9px; font-weight: 800; letter-spacing: .13em; color: #d66b78; margin-bottom: 12px; }
	.analyst-message h3 { font-size: 17px; margin: 0 0 10px; }
	.analyst-message p, .report-card p { font-size: 12px; line-height: 1.9; color: #a4b0be; }
	.approval-note { margin-top: 18px; border-left: 3px solid #c99857; background: #24212a; padding: 15px; }
	.approval-note strong { font-size: 12px; }
	.approval-note p { color: #b9a9ad; font-size: 11px; line-height: 1.7; margin: 7px 0 0; }
	.timeline { margin-top: 32px; border-left: 1px solid #77384a; padding-left: 20px; display: flex; flex-direction: column; gap: 26px; }
	.timeline-entry { position: relative; font-size: 11px; color: #b5c0cb; line-height: 1.7; }
	.timeline-entry::before { content: ''; position: absolute; width: 9px; height: 9px; border-radius: 50%; background: #e43f58; left: -25px; top: 5px; border: 2px solid #111823; }
	.assets-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 13px; margin-top: 24px; }
	.asset-card { background: #0e151f; border: 1px solid #283442; border-radius: 9px; padding: 18px; }
	.asset-top, .asset-bottom { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
	.asset-top strong { font-size: 12px; overflow-wrap: anywhere; }
	.asset-indicator { font-size: 10px; color: #79d8b7; }
	.asset-indicator.offline { color: #f3bb81; }
	.asset-type { margin: 15px 0 25px; font-size: 11px; color: #92a0b2; }
	.asset-bottom { color: #6f8094; font-size: 10px; border-top: 1px solid #2b3645; padding-top: 12px; }
	.report-stats { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin: 24px 0; }
	.report-stats > div { display: flex; flex-direction: column; background: #0b121b; border: 1px solid #2d3745; border-radius: 8px; padding: 16px; }
	.report-stats strong { font-size: 26px; }
	.report-stats span { font-size: 10px; color: #8a98a9; margin-top: 5px; }
	.report-output { background: #19222e; border: 1px solid #4c5263; border-radius: 8px; margin-top: 20px; padding: 17px; }
	.roadmap { display: flex; flex-direction: column; gap: 20px; margin: 34px 0; padding-left: 19px; color: #b3c0ce; font-size: 12px; }
	.roadmap li::marker { color: #e64a5b; }
	.product-footer { display: flex; justify-content: space-between; gap: 15px; font-size: 9px; color: #667488; letter-spacing: .11em; margin-top: 38px; padding-top: 20px; border-top: 1px solid #202938; font-weight: 800; }
	.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; }
	.coverage-quicklink { background: #17202c; border: 1px solid #364052; border-radius: 9px; display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 18px 22px; margin-bottom: 22px; }
	.coverage-key { font-size: 10px; font-weight: 800; letter-spacing: .12em; color: #e47483; display: block; margin-bottom: 9px; }
	.coverage-quicklink strong { font-size: 14px; color: #eff3fa; }
	.coverage-quicklink p { color: #9aacbd; font-size: 11px; line-height: 1.7; margin: 5px 0 0; }
	.coverage-quicklink button { border: 1px solid #784351; border-radius: 6px; padding: 12px; background: #3b2732; color: #f5c6cf; cursor: pointer; font-size: 11px; font-weight: 800; flex-shrink: 0; }
	@media (max-width: 700px) { .coverage-quicklink { flex-direction: column; align-items: flex-start; } }
	.data-source-selector { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; border: 1px solid #3b4251; background: #171f2b; border-radius: 9px; padding: 17px 20px; }
	.data-source-selector strong { font-size: 13px; }
	.data-source-selector p { color: #97a8b9; font-size: 11px; line-height: 1.65; margin: 6px 0 0; }
	.data-source-buttons { display: flex; flex-wrap: wrap; gap: 7px; flex-shrink: 0; }
	.data-source-buttons button { cursor: pointer; padding: 11px 14px; border: 1px solid #3b485b; border-radius: 6px; background: #111b28; color: #b2c0d0; font-size: 11px; font-weight: 800; }
	.data-source-buttons button.chosen { border-color: #b1475a; background: #3b2433; color: #ffccd5; }
	@media (max-width: 750px) { .data-source-selector { flex-direction: column; align-items: flex-start; } }
	@media (max-width: 1260px) {
		.sidebar { width: 222px; flex-basis: 222px; }
		main { padding: 30px 26px; }
		.topbar { padding: 17px 26px; }
		.demo-banner { padding: 9px 26px; }
		.metric-grid { gap: 10px; }
		.metric { padding: 16px; }
		.dashboard-grid { grid-template-columns: 1.3fr 1fr; }
		.incident-layout { grid-template-columns: minmax(0,1.5fr) minmax(275px,1fr); }
		.list-toolbar { flex-wrap: wrap; }
		.search-wrapper { max-width: none; }
	}
	@media (max-width: 1050px) {
		.metric-grid { grid-template-columns: repeat(2,1fr); }
		.dashboard-grid, .incident-layout, .workspace-grid { grid-template-columns: minmax(0,1fr); }
		.assets-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
		.page-heading { align-items: flex-start; flex-direction: column; }
	}
	@media (max-width: 700px) {
		.sidebar { position: fixed; z-index: 50; left: 0; top: 0; transform: translateX(-100%); transition: transform .2s; box-shadow: 10px 0 35px #0007; }
		.sidebar.mobile-open { transform: translateX(0); }
		.mobile-menu { display: inline-block; }
		.demo-banner { padding: 10px 16px; flex-wrap: wrap; }
		.demo-banner > span:nth-child(2) { flex: 1; }
		.topbar { padding: 13px 16px; }
		.signal-tag { display: none; }
		main { padding: 24px 16px; }
		.health-strip { flex-wrap: wrap; }
		.health-badge { margin-left: 0; }
		.metric-grid { gap: 9px; }
		.metric { padding: 13px; }
		.metric-value { font-size: 32px; }
		.signals-panel, .posture-panel, .analyst-card, .timeline-card, .report-card, .assets-panel { padding: 17px; }
		.chart-bars { gap: 4px; }
		.bar-column span { font-size: 8px; transform: rotate(-35deg); }
		.table-head, .case-row { grid-template-columns: minmax(130px,1fr) 70px 73px; gap: 7px; }
		.table-head span:last-child, .time-text { display: none; }
		.state-text { font-size: 9px; }
		.assets-grid { grid-template-columns: 1fr; }
		.product-footer { flex-direction: column; }
		.heading-actions { flex-wrap: wrap; }
	}
</style>
