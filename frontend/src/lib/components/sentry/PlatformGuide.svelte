<script lang="ts">
	import { getGuide, lookupGuide } from '$lib/sentry-contracts/platform-guide';
	import type { SentryView } from '$lib/sentry-contracts/platform-guide';

	/** Deterministic in-app navigation, not connected to a model or chatbot. */
	export let currentView: SentryView;
	export let onNavigate: (view: SentryView) => void;
	let open = false;
	let query = '';
	let selectedView: SentryView | null = null;

	$: results = lookupGuide(query).slice(0, 6);
	$: selected = selectedView ? getGuide(selectedView) : null;
	$: current = getGuide(currentView);

	function navigate(destination: SentryView) {
		open = false;
		query = '';
		selectedView = null;
		onNavigate(destination);
	}
	function toggleGuide() {
		open = !open;
		if (open) {
			query = '';
			selectedView = null;
		}
	}
</script>

<div class="guide">
	<button class="guide-trigger" type="button" on:click={toggleGuide}
		aria-expanded={open} aria-controls="rh-sentry-guide">
		<span aria-hidden="true">⌕</span> Find a feature
	</button>
	{#if open}
		<div class="guide-panel" id="rh-sentry-guide" role="region" aria-label="RH Sentry platform guide">
			<div class="guide-heading">
				<div>
					<strong>Where do you want to go?</strong>
					<p>Search features or tasks. Instructions come from the RH Sentry platform guide—not an AI model.</p>
				</div>
				<button type="button" aria-label="Close platform guide" on:click={toggleGuide}>✕</button>
			</div>
			<label for="rh-guide-search">Find a task or page</label>
			<input id="rh-guide-search" type="search" bind:value={query}
				placeholder="e.g. register an asset, approve a response" />
			<div class="guide-list" aria-label="Matching destinations">
				{#each results as item (item.view)}
					<button type="button" class:chosen={selectedView === item.view} on:click={() => (selectedView = item.view)}>
						<span>{item.title}<small>{item.description}</small></span>
						<span aria-hidden="true">›</span>
					</button>
				{:else}
					<p class="no-match">No matching page is documented yet. Try a feature name or simpler task.</p>
				{/each}
			</div>
			{#if selected}
				<section class="guide-instructions">
					<strong>{selected.title} — how to get there</strong>
					<ol>
						{#each selected.steps as step}
							<li>{step}</li>
						{/each}
					</ol>
					{#if selected.requiresAnalyst}
						<p class="note">Local actions here require an authorised SOC analyst or lead session. Use API Lab to sign in first.</p>
					{/if}
					<button class="open-button" type="button" on:click={() => selected && navigate(selected.view)}>
						Open {selected.title} →
					</button>
				</section>
			{:else}
				<p class="current-hint">Currently in <strong>{current.title}</strong>. Suggested next task:
					<button type="button" on:click={() => navigate(current.next ?? 'Overview')}>{current.nextLabel} →</button>
				</p>
			{/if}
			<p class="guide-disclaimer">A future AI Analyst will use this reviewed navigation catalogue, with permission checks and live page metadata. Automated AI guidance is not enabled.</p>
		</div>
	{/if}
</div>

<style>
	.guide {position:relative;z-index:12}
	.guide-trigger {white-space:nowrap;background:#172334;border:1px solid #34455b;border-radius:7px;color:#dce8f6;font-size:12px;font-weight:750;cursor:pointer;padding:10px 13px}
	.guide-trigger:hover {border-color:#c44b65}
	.guide-trigger span {font-size:17px;color:#e66b83;margin-right:5px;vertical-align:middle}
	.guide-panel {position:absolute;right:0;top:calc(100% + 12px);width:min(430px,calc(100vw - 36px));background:#111b28;border:1px solid #405168;border-radius:11px;box-shadow:0 20px 65px #0009;padding:18px;color:#e8eef7}
	.guide-heading {display:flex;justify-content:space-between;gap:10px;align-items:flex-start;margin-bottom:16px}
	.guide-heading strong {font-size:15px}.guide-heading p {font-size:11px;color:#9eafc1;line-height:1.6;margin:7px 0 0}
	.guide-heading button {background:transparent;border:0;color:#c1d0e0;cursor:pointer;font-size:15px}
	label {font-size:11px;font-weight:750;display:block;color:#a2b8cb;margin-bottom:8px}
	input {background:#0b1420;border:1px solid #3a4a5e;color:#f3f6fa;border-radius:6px;padding:11px 13px;font-size:12px;width:100%}
	.guide-list {margin:12px 0;max-height:205px;overflow-y:auto;border:1px solid #283b4f;border-radius:7px}
	.guide-list button {display:flex;justify-content:space-between;align-items:center;gap:15px;width:100%;background:transparent;border:0;border-bottom:1px solid #283b4f;text-align:left;color:#e9f0f9;padding:11px;cursor:pointer}
	.guide-list button:hover,.guide-list button.chosen {background:#31222e}
	.guide-list button span:first-child {font-size:12px;font-weight:800}
	.guide-list button small {display:block;font-size:10px;color:#97aabd;font-weight:400;margin-top:5px;line-height:1.4}
	.no-match {padding:12px;color:#afc0d1;font-size:12px}
	.guide-instructions {background:#152338;border:1px solid #364b60;border-radius:8px;padding:14px}
	.guide-instructions strong {font-size:12px}
	.guide-instructions ol {margin:12px 0 13px;padding-left:20px;font-size:11px;color:#b3c5d7;line-height:1.8}
	.note {font-size:11px;color:#f2c49a;line-height:1.6}
	.open-button {background:#d93654;color:#fff;border:0;border-radius:6px;padding:10px 13px;font-size:11px;font-weight:800;cursor:pointer}
	.current-hint {font-size:11px;line-height:1.6;color:#a6b8cb}
	.current-hint button {color:#f09ab0;border:0;background:none;cursor:pointer;font-size:11px;margin-left:6px;text-decoration:underline}
	.guide-disclaimer {font-size:10px;color:#8095ab;line-height:1.6;border-top:1px solid #293a4c;padding-top:12px}
	@media(max-width:680px){.guide-panel{position:fixed;top:75px;right:10px;left:10px;width:auto;max-height:calc(100dvh - 90px);overflow:auto}}
</style>
