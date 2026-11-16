<script lang="ts">
	import type { DemoIncident } from '$lib/sentry-demo/types';
	import type { DemoCustomer } from '$lib/sentry-demo/customer';

	export let customer: DemoCustomer;
	export let incidents: DemoIncident[];
	export let onExit: () => void;

	type Tab = 'Overview' | 'Incidents' | 'Services';
	const tabs: Tab[] = ['Overview', 'Incidents', 'Services'];
	let tab: Tab = 'Overview';
	let expandedId: string | null = null;
	$: openCases = incidents.filter((incident) => incident.status !== 'Contained').length;
	$: priorityCases = incidents.filter((incident) => ['Critical', 'High'].includes(incident.severity)).length;
	$: selected = incidents.find((incident) => incident.id === expandedId) ?? null;

	function showTab(next: Tab) {
		tab = next;
		expandedId = null;
	}
</script>

<div class="customer-sandbox">
	<header class="customer-header">
		<div class="customer-brand">
			<div class="brand-mark" aria-hidden="true">RH</div>
			<div class="brand-text"><strong>SENTRY<span>.</span></strong><small>YOUR SECURITY OVERVIEW</small></div>
		</div>
		<div class="header-right">
			<span class="demo-tag">CUSTOMER EXPERIENCE CONCEPT</span>
			<button type="button" on:click={onExit}>← Exit customer preview</button>
		</div>
	</header>

	<div class="customer-warning" role="status">
		<strong>VISUAL DEMONSTRATION</strong>
		<span>Fictional customer, incidents and services. No authentication, tenant isolation or live monitoring exists in this preview.</span>
	</div>

	<div class="customer-content">
		<div class="greeting">
			<div>
				<div class="eyebrow">WELCOME TO RH SENTRY</div>
				<h2>{customer.name}</h2>
				<p>One place to understand your security position and the actions that matter.</p>
			</div>
			<div class="customer-id">
				<span>DEMO ORGANISATION</span>
				<strong>{customer.sectorCode} / {customer.region}</strong>
			</div>
		</div>

		<div class="customer-tabs" aria-label="Customer portal sections">
			{#each tabs as item}
				<button type="button" class:active={tab === item} aria-pressed={tab === item} on:click={() => showTab(item)}>{item}</button>
			{/each}
		</div>

		{#if tab === 'Overview'}
			<div class="intro-band">
				<div class="intro-symbol" aria-hidden="true">◎</div>
				<div><strong>Your security overview</strong><p>Actual monitoring will appear here once the SOC backend, agents and account authorisation have been implemented and validated.</p></div>
				<span>NOT CONNECTED</span>
			</div>
			<div class="stat-row">
				<div class="stat"><span>LIVE MONITORED DEVICES</span><strong>00</strong><small>No connected agents</small></div>
				<div class="stat"><span>EXAMPLE ASSETS</span><strong>{customer.exampleAssets}</strong><small>Fictional inventory</small></div>
				<div class="stat"><span>OPEN EXAMPLE CASES</span><strong>{openCases.toString().padStart(2, '0')}</strong><small>Demonstration incidents</small></div>
				<div class="stat"><span>HIGH-PRIORITY EXAMPLES</span><strong class="danger">{priorityCases.toString().padStart(2, '0')}</strong><small>Not live security alerts</small></div>
			</div>
			<div class="overview-grid">
				<section class="section-card">
					<div class="section-header"><div><div class="eyebrow">PRIORITY INTELLIGENCE</div><h3>Cases that need attention</h3></div><button type="button" on:click={() => showTab('Incidents')}>View all cases ↗</button></div>
					{#each incidents.filter((incident) => incident.status !== 'Contained').slice(0, 3) as incident (incident.id)}
						<div class="case-line"><span class="case-flag">!</span><div><strong>{incident.title}</strong><small>{incident.id} · {incident.status}</small></div><span class:critical={incident.severity === 'Critical'} class="case-severity">{incident.severity}</span></div>
					{:else}
						<div class="empty">No open sample cases for this fictional organisation.</div>
					{/each}
				</section>
				<section class="section-card services-summary">
					<div class="eyebrow">SERVICE VISIBILITY</div><h3>Protection status</h3>
					<div class="service-line"><span>Endpoint detection</span><strong>Not connected</strong></div>
					<div class="service-line"><span>Identity monitoring</span><strong>Not connected</strong></div>
					<div class="service-line"><span>Incident response</span><strong>Demo only</strong></div>
					<div class="service-line"><span>AI investigations</span><strong>Not connected</strong></div>
					<button type="button" on:click={() => showTab('Services')}>Explore planned services ↗</button>
				</section>
			</div>
		{:else if tab === 'Incidents'}
			<section class="section-card">
				<div class="section-header"><div><div class="eyebrow">YOUR ORGANISATION / SAMPLE DATA</div><h3>Security investigations</h3></div><span class="count">{incidents.length} SAMPLE CASES</span></div>
				<p class="description">Only cases assigned to this demonstration organisation are shown. Real separation will require enforced server-side authorisation, not this visual filter.</p>
				{#each incidents as incident (incident.id)}
					<div class="incident-block">
						<button type="button" class="incident-toggle" aria-expanded={expandedId === incident.id} on:click={() => (expandedId = expandedId === incident.id ? null : incident.id)}>
							<div><strong>{incident.title}</strong><small>{incident.id} · {incident.asset}</small></div>
							<div class="incident-state"><span>{incident.severity} · {incident.status}</span><b aria-hidden="true">{expandedId === incident.id ? '−' : '+'}</b></div>
						</button>
						{#if selected?.id === incident.id}
							<div class="case-description">
								<p>{selected.description}</p>
								<strong>EXAMPLE OBSERVATIONS</strong>
								<ul>{#each selected.indicators as item}<li>{item}</li>{/each}</ul>
								<p class="tiny-note">Illustrative incident content only; not a confirmed threat assessment.</p>
							</div>
						{/if}
					</div>
				{:else}
					<div class="empty">No example cases are assigned to this organisation.</div>
				{/each}
			</section>
		{:else}
			<section class="section-card">
				<div class="eyebrow">THE RH SENTRY SERVICE EXPERIENCE</div><h3>Your protection services</h3>
				<p class="description">This is a proposed feature catalogue. Subscription billing, support contracts and service management have not been built.</p>
				<div class="service-cards">
					<div><span class="service-icon" aria-hidden="true">01</span><strong>Security monitoring</strong><p>Managed telemetry collection, alerts and detection coverage once connected.</p><small>PLANNED · NOT ACTIVE</small></div>
					<div><span class="service-icon" aria-hidden="true">02</span><strong>AI-assisted investigations</strong><p>Explainable investigations, evidence timelines and analyst escalation.</p><small>PLANNED · NOT ACTIVE</small></div>
					<div><span class="service-icon" aria-hidden="true">03</span><strong>Response coordination</strong><p>Approval-based containment and documented incident handling.</p><small>PLANNED · NOT ACTIVE</small></div>
					<div><span class="service-icon" aria-hidden="true">04</span><strong>Executive reporting</strong><p>Understand changes in risk, monitoring coverage and incident outcomes.</p><small>PLANNED · NOT ACTIVE</small></div>
				</div>
			</section>
		{/if}

		<footer>RH SENTRY · RED HORIZON CYBER GROUP <span>LOCAL PRODUCT DESIGN ONLY / NO REAL CUSTOMER DATA</span></footer>
	</div>
</div>

<style>
	.customer-sandbox { border: 1px solid #273648; border-radius: 12px; background: #0b111a; overflow: hidden; color: #edf2f9; font-family: Inter, 'Segoe UI', Arial, sans-serif; }
	.customer-header { display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 21px 27px; border-bottom: 1px solid #293344; background: #101824; }
	.customer-brand { display: flex; align-items: center; gap: 12px; }
	.brand-mark { height: 36px; width: 36px; border-radius: 8px; display: grid; place-items: center; background: #3a202c; border: 1px solid #8d4154; color: #ffdce2; font-weight: 800; font-size: 12px; }
	.brand-text { display: flex; flex-direction: column; gap: 4px; }
	.brand-text strong { font-size: 19px; font-weight: 850; letter-spacing: .04em; }
	.brand-text strong span { color: #e4465d; }
	.brand-text small { font-size: 10px; letter-spacing: .13em; color: #8799ad; font-weight: 750; }
	.header-right { display: flex; align-items: center; flex-wrap: wrap; gap: 15px; }
	.demo-tag { font-size: 10px; color: #f1c2ca; border: 1px solid #704355; background: #352430; padding: 9px 11px; border-radius: 5px; font-weight: 750; }
	.header-right button,.section-header button,.services-summary button { border: 1px solid #435064; background: #172232; color: #d7e2ef; cursor: pointer; padding: 10px 13px; border-radius: 6px; font-size: 11px; font-weight: 750; }
	.header-right button:hover,.section-header button:hover,.services-summary button:hover { background: #253348; }
	.customer-warning { display: flex; align-items: center; gap: 12px; padding: 14px 27px; border-bottom: 1px solid #534039; background: #242126; font-size: 11px; line-height: 1.6; color: #dbc6bd; }
	.customer-warning strong { white-space: nowrap; color: #f9d4a7; font-size: 10px; letter-spacing: .07em; }
	.customer-content { padding: 33px 31px 24px; }
	.greeting { display: flex; justify-content: space-between; gap: 20px; align-items: flex-end; }
	.eyebrow { color: #e16b7a; font-size: 10px; font-weight: 800; letter-spacing: .12em; }
	.greeting h2 { font-size: 27px; letter-spacing: -.03em; font-weight: 780; margin: 10px 0; }
	.greeting p,.description { color: #a5b2c4; font-size: 13px; line-height: 1.7; margin: 0; }
	.customer-id { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
	.customer-id span { font-size: 10px; letter-spacing: .08em; color: #8090a4; }
	.customer-id strong { font-size: 12px; color: #c4d0de; }
	.customer-tabs { display: flex; gap: 25px; border-bottom: 1px solid #2d3949; margin: 31px 0 23px; }
	.customer-tabs button { border: 0; border-bottom: 2px solid transparent; background: transparent; color: #98a8ba; padding: 12px 2px 14px; cursor: pointer; font-size: 12px; font-weight: 750; }
	.customer-tabs button.active { border-color: #eb5167; color: #ffffff; }
	.intro-band { border: 1px solid #3a414b; background: linear-gradient(110deg, #22232d, #161c2a); border-radius: 9px; padding: 20px; display: flex; align-items: center; gap: 15px; }
	.intro-symbol { color: #e5bd8a; font-size: 30px; border: 1px solid #845642; border-radius: 50%; width: 44px; height: 44px; display: grid; place-items: center; flex-shrink: 0; }
	.intro-band strong { font-size: 14px; }
	.intro-band p { color: #b2b6c6; font-size: 11px; line-height: 1.65; margin: 6px 0 0; }
	.intro-band>span { white-space: nowrap; margin-left: auto; color: #f4c48b; border: 1px solid #866343; border-radius: 4px; font-size: 10px; padding: 7px 10px; }
	.stat-row { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 12px; margin: 20px 0; }
	.stat { border: 1px solid #2d3949; background: #121b27; border-radius: 8px; padding: 17px; display: flex; flex-direction: column; gap: 10px; min-width: 0; }
	.stat span { color: #94a4b8; font-size: 10px; font-weight: 750; letter-spacing: .07em; }
	.stat strong { font-size: 29px; font-weight: 770; }
	.stat strong.danger { color: #f16a7b; }
	.stat small { color: #8394a9; font-size: 11px; }
	.overview-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px; }
	.section-card { border: 1px solid #2b394a; background: #121b26; border-radius: 10px; padding: 24px; min-width: 0; }
	.section-header { display: flex; justify-content: space-between; gap: 14px; align-items: center; margin-bottom: 15px; }
	.section-card h3 { font-size: 17px; font-weight: 750; margin: 9px 0 15px; }
	.case-line { display: flex; align-items: center; gap: 12px; padding: 18px 0; border-top: 1px solid #2b394a; }
	.case-line strong,.incident-toggle strong { display: block; font-size: 12px; color: #e5edf6; }
	.case-line small,.incident-toggle small { display: block; color: #93a2b5; font-size: 11px; margin-top: 7px; }
	.case-flag { background: #3e2430; border: 1px solid #7b4052; color: #ffc1cb; padding: 9px 13px; border-radius: 6px; }
	.case-severity { margin-left: auto; font-size: 11px; color: #f0ad81; }
	.case-severity.critical { color: #fa8397; }
	.service-line { display: flex; justify-content: space-between; gap: 12px; border-top: 1px solid #2c3949; padding: 16px 0; font-size: 12px; color: #b3c0ce; }
	.service-line strong { color: #f2ba83; font-size: 11px; text-align: right; }
	.services-summary button { width: 100%; margin-top: 15px; }
	.section-header .count { color: #92a2b5; white-space: nowrap; font-size: 10px; }
	.incident-block { border-top: 1px solid #2b394a; }
	.incident-toggle { width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 16px; background: transparent; border: 0; cursor: pointer; text-align: left; color: #e9eef6; padding: 19px 0; }
	.incident-state { display: flex; align-items: center; gap: 17px; color: #f2afbc; font-size: 11px; }
	.incident-state b { font-size: 19px; }
	.case-description { background: #0c141e; border: 1px solid #2a3848; padding: 20px; border-radius: 7px; margin-bottom: 12px; }
	.case-description p,.case-description li { color: #aebccd; line-height: 1.75; font-size: 12px; }
	.case-description strong { font-size: 10px; letter-spacing: .1em; color: #e5a3ad; }
	.case-description ul { padding-left: 21px; }
	.case-description .tiny-note { color: #f0bb87; font-size: 11px; }
	.empty { padding: 22px 0; color: #9cabbf; font-size: 12px; }
	.service-cards { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 13px; margin-top: 22px; }
	.service-cards>div { display: flex; flex-direction: column; padding: 21px; border: 1px solid #314052; background: #0d1621; border-radius: 8px; gap: 12px; }
	.service-icon { background: #3b2632; color: #f9b2bf; width: 37px; height: 37px; border-radius: 7px; display: grid; place-items: center; font-size: 12px; font-weight: 800; }
	.service-cards strong { font-size: 14px; }
	.service-cards p { color: #9eafc0; font-size: 12px; line-height: 1.7; flex: 1; margin: 0; }
	.service-cards small { color: #efb88b; font-size: 10px; }
	.customer-content footer { display: flex; justify-content: space-between; gap: 15px; margin-top: 32px; padding-top: 18px; border-top: 1px solid #2a3545; font-size: 10px; color: #788ca2; letter-spacing: .08em; }
	@media (max-width: 1050px) { .stat-row { grid-template-columns: repeat(2,minmax(0,1fr)); } .overview-grid { grid-template-columns: 1fr; } }
	@media (max-width: 650px) { .customer-header,.greeting,.intro-band { flex-direction: column; align-items: flex-start; } .customer-warning { flex-wrap: wrap; } .customer-content { padding: 21px 16px; } .customer-id { align-items: flex-start; } .service-cards { grid-template-columns: 1fr; } .customer-content footer { flex-direction: column; } .intro-band>span { margin: 0; } .section-header,.incident-toggle { flex-direction: column; align-items: flex-start; } }
</style>
