<script lang="ts">
	import type { DemoIncident } from '$lib/sentry-demo/types';
	import { demoCustomers, incidentsForDemoCustomer } from '$lib/sentry-demo/customer';
	import CustomerPortalPreview from '$lib/components/sentry/CustomerPortalPreview.svelte';
	export let incidents: DemoIncident[];

	const customers = demoCustomers;
	let selectedId = 'northbridge';
	let customerPreview = false;
	let search = '';
	$: customer = customers.find((c) => c.id === selectedId) ?? customers[0];
	$: visibleCustomers = customers.filter((c) => (c.name + ' ' + c.sector).toLowerCase().includes(search.trim().toLowerCase()));
	$: customerIncidents = incidentsForDemoCustomer(incidents, selectedId);
	$: customerOpen = customerIncidents.filter((incident) => incident.status !== 'Contained').length;
	$: customerHigh = customerIncidents.filter((incident) => incident.severity === 'Critical' || incident.severity === 'High').length;
	function selectCustomer(id: string) {
		selectedId = id;
		customerPreview = false;
	}
</script>

<div class="clients-layout" class:customer-mode={customerPreview}>
	{#if customerPreview}
		<CustomerPortalPreview {customer} incidents={customerIncidents} onExit={() => (customerPreview = false)} />
	{:else}
	<aside class="clients-list panel">
		<div class="list-heading">
			<span class="label-accent">MSSP / DEMONSTRATION</span>
			<h2>Customer portfolio</h2>
			<p>Fictional organisations for testing the multi-client RH Sentry interface.</p>
		</div>
		<div class="customer-search"><label for="sentry-customer-search">Find demo organisation</label><input id="sentry-customer-search" bind:value={search} placeholder="Search customers..." type="search" /></div>
		<div class="customer-list">
			{#each visibleCustomers as c (c.id)}
				<button type="button" class:chosen={c.id === selectedId} aria-pressed={c.id === selectedId} on:click={() => selectCustomer(c.id)}>
					<span class="avatar">{c.sectorCode}</span>
					<span class="customer-copy"><strong>{c.name}</strong><small>{c.sector}</small></span>
					<span class="arrow" aria-hidden="true">›</span>
				</button>
			{:else}
				<p class="no-results">No sample customers match.</p>
			{/each}
		</div>
		<div class="list-disclaimer">No real tenants, subscriptions, users or customer databases are connected.</div>
	</aside>

	<section class="customer-detail panel">
		<div class="detail-header">
			<div><div class="label-accent">{customerPreview ? 'CUSTOMER-VIEW MOCKUP' : 'OPERATOR / CUSTOMER CONTEXT'}</div><h2>{customer.name}</h2><p>{customer.sector} <span>·</span> {customer.region}</p></div>
			<span class="demo-label">SAMPLE CUSTOMER</span>
		</div>
		<div class="view-switch" aria-label="Preview user experience">
			<button type="button" class:active={!customerPreview} aria-pressed={!customerPreview} on:click={() => (customerPreview = false)}>SOC operator view</button>
			<button type="button" class:active={customerPreview} aria-pressed={customerPreview} on:click={() => (customerPreview = true)}>Customer portal preview</button>
		</div>
		<div class="preview-warning">
			<strong>{customerPreview ? 'Customer portal appearance only' : 'Operator workspace preview'}</strong>
			<p>{customerPreview ? 'This view demonstrates how a customer dashboard might look. Switching views is not authentication or tenant isolation, and would not be a suitable access control.' : 'In a live SOC, only authorised operator roles should have cross-customer visibility. All data here is fictional.'}</p>
		</div>
		<div class="metrics">
			<div class="metric"><span>LIVE AGENTS</span><strong>00</strong><small>No monitoring connected</small></div>
			<div class="metric"><span>SAMPLE ASSETS</span><strong>{customer.exampleAssets}</strong><small>Design placeholders</small></div>
			<div class="metric"><span>OPEN DEMO CASES</span><strong>{customerOpen.toString().padStart(2, '0')}</strong><small>Selected demo organisation only</small></div>
			<div class="metric"><span>HIGH-PRIORITY CASES</span><strong class="danger">{customerHigh.toString().padStart(2, '0')}</strong><small>Illustrative severity</small></div>
		</div>
		<div class="case-section">
			<div class="section-heading"><div><span class="label-accent">DEMONSTRATION INCIDENTS</span><h3>{customerPreview ? 'Your organisation’s case summary' : 'Customer investigation overview'}</h3></div><span>{customerIncidents.length} SAMPLE CASES</span></div>
			{#each customerIncidents as incident (incident.id)}
				<div class="incident-line">
					<div class="case-icon" aria-hidden="true">!</div>
					<div><strong>{incident.title}</strong><p>{incident.id} <span>·</span> {incident.asset}</p></div>
					<div class="case-status"><span class:critical={incident.severity === 'Critical'} class:high={incident.severity === 'High'}>{incident.severity}</span><small>{incident.status}</small></div>
				</div>
			{:else}
				<p class="empty">No sample incidents assigned to this organisation.</p>
			{/each}
		</div>
		{#if !customerPreview}
			<div class="operator-metadata"><span>EXAMPLE CUSTOMER CONTACT</span><strong>{customer.demoContact}</strong><small>Reserved .invalid demonstration address — not a real customer.</small></div>
		{:else}
			<div class="customer-footer"><strong>RH Sentry customer experience</strong><p>Planned features: customer-verified access, scoped incidents, exposure trends, reporting and managed response status. None are connected yet.</p></div>
		{/if}
	</section>
	{/if}
</div>

<style>
	.clients-layout { display: grid; grid-template-columns: minmax(260px, .72fr) minmax(0, 1.95fr); gap: 17px; align-items: start; }
	.clients-layout.customer-mode { grid-template-columns: minmax(0,1fr); }
	.panel { border: 1px solid #293442; border-radius: 11px; background: #111823; overflow: hidden; min-width: 0; }
	.list-heading { padding: 25px 21px 18px; }
	.label-accent { color: #e16776; font-size: 10px; font-weight: 800; letter-spacing: .12em; }
	h2 { font-size: 22px; line-height: 1.35; margin: 9px 0; color: #f3f6fa; font-weight: 750; }
	.list-heading p, .detail-header p { color: #9cacbe; font-size: 12px; line-height: 1.6; margin: 8px 0 0; }
	.customer-search { padding: 0 17px 17px; }
	.customer-search label { display: block; font-size: 11px; color: #9eacbf; margin-bottom: 9px; }
	.customer-search input { width: 100%; background: #0a111b; border: 1px solid #364254; color: #eff3fa; font-size: 12px; padding: 13px; border-radius: 7px; }
	.customer-list { border-top: 1px solid #2b3542; }
	.customer-list button { display: flex; align-items: center; gap: 13px; padding: 17px; width: 100%; text-align: left; border: 0; border-bottom: 1px solid #25303e; background: transparent; color: #e7edf4; cursor: pointer; }
	.customer-list button:hover { background: #1b2634; }
	.customer-list button.chosen { background: #2b1e2b; box-shadow: inset 3px 0 0 #e24159; }
	.avatar { border: 1px solid #674052; color: #ffb9c2; background: #412332; border-radius: 8px; height: 39px; width: 39px; flex-shrink: 0; display: grid; place-items: center; font-size: 11px; font-weight: 800; }
	.customer-copy { display: flex; flex-direction: column; min-width: 0; gap: 5px; }
	.customer-copy strong { font-size: 12px; line-height: 1.35; }
	.customer-copy small { font-size: 11px; color: #8798a9; }
	.arrow { margin-left: auto; color: #e76273; }
	.no-results,.list-disclaimer { padding: 18px; color: #8595aa; font-size: 11px; line-height: 1.6; }
	.list-disclaimer { background: #151d29; }
	.customer-detail { padding: 26px; }
	.detail-header { display: flex; justify-content: space-between; align-items: start; gap: 12px; }
	.detail-header p span { color: #e24b60; margin: 0 8px; }
	.demo-label { color: #f1b6c0; font-size: 10px; letter-spacing: .04em; background: #372330; padding: 9px; border: 1px solid #704254; border-radius: 5px; white-space: nowrap; }
	.view-switch { display: flex; gap: 8px; margin: 27px 0 18px; }
	.view-switch button { cursor: pointer; border: 1px solid #344052; background: #151e2b; color: #a9b8c9; border-radius: 7px; padding: 12px 16px; font-size: 12px; font-weight: 700; }
	.view-switch button.active { background: #3a2231; border-color: #b54558; color: #f5c0c8; }
	.preview-warning { background: #252329; border-left: 3px solid #bd915f; padding: 14px 17px; }
	.preview-warning strong { color: #e8cba7; font-size: 12px; }
	.preview-warning p { color: #c3b8bd; font-size: 11px; line-height: 1.65; margin: 7px 0 0; }
	.metrics { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; margin: 25px 0; }
	.metric { border: 1px solid #2d3948; background: #0d151f; border-radius: 8px; padding: 17px; display: flex; flex-direction: column; gap: 7px; }
	.metric span { color: #8798ac; font-size: 10px; font-weight: 800; letter-spacing: .07em; }
	.metric strong { color: #f3f6fa; font-size: 28px; line-height: 1.25; }
	.metric strong.danger { color: #ed6174; }
	.metric small { color: #8191a5; font-size: 10px; line-height: 1.45; }
	.section-heading { display: flex; justify-content: space-between; gap: 10px; align-items: end; padding-bottom: 17px; }
	.section-heading h3 { margin: 9px 0 0; font-size: 17px; font-weight: 750; color: #eaf0f8; }
	.section-heading > span { font-size: 10px; color: #8a98ab; font-weight: 750; letter-spacing: .06em; }
	.case-section { border: 1px solid #2d3948; border-radius: 9px; background: #0e1520; padding: 20px; }
	.incident-line { display: flex; gap: 13px; align-items: center; border-top: 1px solid #273343; padding: 17px 0; }
	.case-icon { background: #3f2431; border: 1px solid #7a3c50; color: #f2adba; display: grid; place-items: center; border-radius: 7px; width: 35px; height: 35px; flex-shrink: 0; font-weight: 900; }
	.incident-line > div:nth-child(2) { min-width: 0; }
	.incident-line strong { font-size: 12px; color: #e8eff7; }
	.incident-line p { font-size: 11px; color: #8698ae; margin: 7px 0 0; overflow-wrap: anywhere; }
	.incident-line p span { color: #e46779; padding: 0 5px; }
	.case-status { margin-left: auto; text-align: right; display: flex; flex-direction: column; gap: 8px; font-size: 11px; color: #afbbc9; flex-shrink: 0; }
	.case-status span.critical { color: #fa7e8f; }
	.case-status span.high { color: #f2b878; }
	.case-status small { color: #8496ad; }
	.empty { color: #97a4b5; font-size: 12px; }
	.operator-metadata,.customer-footer { background: #182231; border: 1px solid #364356; border-radius: 7px; padding: 19px; margin-top: 22px; display: flex; flex-direction: column; gap: 8px; }
	.operator-metadata span { color: #a4b4c5; letter-spacing: .09em; font-size: 10px; font-weight: 750; }
	.operator-metadata strong { font-size: 12px; overflow-wrap: anywhere; }
	.operator-metadata small, .customer-footer p { color: #8497aa; font-size: 11px; line-height: 1.6; margin: 0; }
	.customer-footer strong { font-size: 13px; }
	@media(max-width:1150px) { .clients-layout { grid-template-columns: 1fr; } .metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } }
	@media(max-width:650px) { .customer-detail { padding: 18px; } .detail-header,.section-heading { flex-direction: column; align-items: flex-start; } .metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } .incident-line { flex-wrap: wrap; } .view-switch { flex-wrap: wrap; } }
</style>
