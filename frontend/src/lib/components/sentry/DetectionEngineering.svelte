<script lang="ts">
	import {
		demoDetectionRules,
		demoTelemetrySources,
		demoCoverageSummary,
		evaluateDemoDetection
	} from '$lib/sentry-demo/detection';
	import type {
		DemoDetectionResult,
		DemoDetectionRule
	} from '$lib/sentry-demo/detection';

	export let onOpenIncident: (id: string) => void;

	type View = 'Rule library' | 'Monitoring coverage' | 'Test laboratory';
	const tabs: View[] = ['Rule library', 'Monitoring coverage', 'Test laboratory'];
	const families = ['All', ...Array.from(new Set(demoDetectionRules.map((rule) => rule.family)))];
	let tab: View = 'Rule library';
	let search = '';
	let family = 'All';
	let selectedId = demoDetectionRules[0].id;
	let selectedTestId = demoDetectionRules[0].tests[0].id;
	let result: DemoDetectionResult | null = null;
	let completedRuns = 0;
	let testedRuleCount = 0;
	let runKeys: string[] = [];
	const coverage = demoCoverageSummary();

	$: rule = demoDetectionRules.find((item) => item.id === selectedId) ?? demoDetectionRules[0];
	$: chosenTest = rule.tests.find((example) => example.id === selectedTestId) ?? rule.tests[0];
	$: visibleRules = demoDetectionRules.filter((item) =>
		(family === 'All' || item.family === family) &&
		(!search.trim() || [item.name, item.id, item.family, item.technique, item.summary].join(' ').toLowerCase().includes(search.trim().toLowerCase()))
	);
	$: linkedSource = demoTelemetrySources.find((source) => source.id === rule.sourceId);

	function selectRule(next: DemoDetectionRule) {
		selectedId = next.id;
		selectedTestId = next.tests[0].id;
		result = null;
	}
	function openLab(next?: DemoDetectionRule) {
		if (next) selectRule(next);
		tab = 'Test laboratory';
	}
	function selectTest(id: string) {
		selectedTestId = id;
		result = null;
	}
	function handleRuleChange(event: Event) {
		const element = event.currentTarget;
		if (!(element instanceof HTMLSelectElement)) return;
		const next = demoDetectionRules.find((entry) => entry.id === element.value);
		if (next) selectRule(next);
	}
	function runTest() {
		// No API, local shell, Wazuh, endpoint or response action is invoked.
		result = evaluateDemoDetection(rule.id, chosenTest.event);
		completedRuns += 1;
		const key = rule.id + ':' + chosenTest.id;
		if (!runKeys.includes(key)) runKeys = [...runKeys, key];
		testedRuleCount = new Set(runKeys.map((entry) => entry.split(':')[0])).size;
	}
</script>

<div class="detector">
	<div class="intro">
		<div class="intro-icon" aria-hidden="true">◈</div>
		<div class="intro-copy">
			<strong>Detection engineering, designed for visibility.</strong>
			<p>Explore example detection logic, understand missing telemetry and validate synthetic cases. This is a design laboratory—not an operational SIEM or rule deployment interface.</p>
		</div>
		<span class="intro-status">NO LIVE RULES</span>
	</div>

	<div class="metrics" aria-label="Detection preview metrics">
		<div><span>DEMO DETECTION RULES</span><strong>{coverage.exampleRules.toString().padStart(2, '0')}</strong><small>Illustrative rules only</small></div>
		<div><span>LIVE DATA SOURCES</span><strong>00</strong><small>of {coverage.sourceTypes} proposed sources</small></div>
		<div><span>LIVE DETECTION COVERAGE</span><strong>0%</strong><small>No telemetry connected</small></div>
		<div><span>DEMO TESTS RUN</span><strong>{completedRuns.toString().padStart(2, '0')}</strong><small>{testedRuleCount} example rules exercised</small></div>
	</div>

	<div class="tabs" aria-label="Detection engineering sections">
		{#each tabs as item}
			<button type="button" aria-pressed={tab === item} class:active={tab === item} on:click={() => (tab = item)}>{item}</button>
		{/each}
	</div>

	{#if tab === 'Rule library'}
		<div class="rule-grid">
			<section class="card rules">
				<div class="card-heading"><div><span class="overline">ENGINEERING / SAMPLE CONTENT</span><h2>Detection rule library</h2></div><span class="count">{visibleRules.length} RULES</span></div>
				<div class="rule-filters">
					<label for="sentry-rule-search" class="sr-only">Search demonstration rules</label>
					<input id="sentry-rule-search" type="search" bind:value={search} placeholder="Search rule, technique or category..." />
					<label for="sentry-family" class="sr-only">Filter detection family</label>
					<select id="sentry-family" bind:value={family}>
						{#each families as item}<option value={item}>{item === 'All' ? 'All detection families' : item}</option>{/each}
					</select>
				</div>
				<div class="rule-list">
					{#each visibleRules as item (item.id)}
						<button type="button" class:chosen={rule.id === item.id} aria-pressed={rule.id === item.id} on:click={() => selectRule(item)}>
							<div class="rule-top"><span>{item.id}</span><span class:critical={item.severity === 'Critical'} class:high={item.severity === 'High'}>{item.severity}</span></div>
							<strong>{item.name}</strong>
							<small>{item.family} · {item.technique}</small>
							<div class="rule-foot"><span>EXAMPLE DEFINITION</span><span aria-hidden="true">›</span></div>
						</button>
					{:else}
						<div class="empty">No rules match your search. Try another detection family or remove the query.</div>
					{/each}
				</div>
			</section>

			<section class="card rule-detail">
				<div class="card-heading"><div><span class="overline">SELECTED DETECTION / {rule.id}</span><h2>Rule definition</h2></div><span class="demo-flag">NOT DEPLOYED</span></div>
				<div class="detail-hero"><span class="overline">{rule.family.toUpperCase()}</span><h3>{rule.name}</h3><p>{rule.summary}</p></div>
				<div class="detail-fields">
					<div><span>SEVERITY</span><strong>{rule.severity}</strong></div>
					<div><span>ATT&CK TECHNIQUE CONTEXT</span><strong>{rule.technique}</strong></div>
					<div><span>TACTIC / CATEGORY</span><strong>{rule.tactic}</strong></div>
					<div><span>DATA SOURCE</span><strong>{linkedSource?.name ?? 'Unmapped sample'}</strong></div>
				</div>
				<div class="logic"><div class="overline">ILLUSTRATIVE DETECTION PREDICATE</div><p>{rule.logic}</p><small>Readable example only. This is not Sigma, YARA, Wazuh rule syntax or a production-tested detector.</small></div>
				<div class="false-positives"><span class="overline">KNOWN BENIGN EXPLANATIONS TO CONSIDER</span><ul>{#each rule.falsePositives as item}<li>{item}</li>{/each}</ul></div>
				<div class="source-gap"><strong>Current monitoring gap</strong><p>{linkedSource?.gap ?? 'Source integration has not been designed.'}</p><span>No live events are available.</span></div>
				<div class="buttons"><button type="button" class="primary" on:click={() => openLab(rule)}>Run sample test ↗</button><button type="button" class="secondary" on:click={() => onOpenIncident(rule.linkedIncidentId)}>View linked demo incident ↗</button></div>
			</section>
		</div>
	{:else if tab === 'Monitoring coverage'}
		<div class="coverage-intro card">
			<div><span class="overline">MONITORING QUALITY / NOT CONNECTED</span><h2>Coverage gaps are part of the security picture.</h2><p>Six example telemetry source types are proposed for the eventual SOC. None has an agent, API connector or event stream connected. The matrix below reflects integration requirements—not real security exposure or a measured MITRE ATT&CK coverage score.</p></div>
			<div class="coverage-number"><strong>0%</strong><small>VERIFIED LIVE COVERAGE</small></div>
		</div>
		<div class="sources">
			{#each demoTelemetrySources as source (source.id)}
				<article class="card source">
					<div class="source-heading"><span class="source-icon" aria-hidden="true">{source.category.slice(0,2)}</span><span class="source-health">● NOT CONNECTED</span></div>
					<div class="overline">{source.category}</div><h3>{source.name}</h3><p>{source.description}</p>
					<div class="source-field"><span>EVENTS REQUIRED</span><strong>{source.requiredEvents}</strong></div>
					<div class="source-field gap"><span>KNOWN IMPLEMENTATION GAP</span><strong>{source.gap}</strong></div>
					<div class="source-footer">Planned integration <span>·</span> 0 live sensors</div>
				</article>
			{/each}
		</div>
		<div class="coverage-footer card"><div><span class="overline">IMPORTANT DISTINCTION</span><h3>Potential technique coverage is not proof of detection.</h3><p>Even after event collection is connected, each rule must be tested for actual telemetry availability, accuracy, false positives, coverage of relevant ATT&CK techniques and operational performance before RH Sentry makes a protection claim.</p></div><button type="button" on:click={() => (tab = 'Test laboratory')}>Explore demo testing ↗</button></div>
	{:else}
		<div class="lab-grid">
			<section class="card lab-chooser">
				<div class="card-heading"><div><span class="overline">RULE VALIDATION / SYNTHETIC</span><h2>Test laboratory</h2></div><span class="demo-flag">LOCAL ONLY</span></div>
				<div class="chooser-group">
					<label for="lab-rule">DETECTION RULE</label>
					<select id="lab-rule" value={selectedId} on:change={handleRuleChange}>
						{#each demoDetectionRules as item}<option value={item.id}>{item.name}</option>{/each}
					</select>
				</div>
				<div class="chooser-group"><span class="chooser-title">SELECT SAMPLE EVENT</span>
					{#each rule.tests as item (item.id)}
						<button type="button" class:chosen={chosenTest.id === item.id} class="test-choice" aria-pressed={chosenTest.id === item.id} on:click={() => selectTest(item.id)}>
							<span class="radio-mark" aria-hidden="true">{chosenTest.id === item.id ? '●' : '○'}</span>
							<span><strong>{item.name}</strong><small>{item.description}</small></span>
						</button>
					{/each}
				</div>
				<div class="sample-input"><div class="overline">SYNTHETIC EVENT FIELDS</div><pre>{JSON.stringify(chosenTest.event, null, 2)}</pre></div>
			</section>

			<section class="card lab-output">
				<div class="card-heading"><div><span class="overline">DETERMINISTIC PREDICATE CHECK</span><h2>Test result</h2></div><span class="demo-flag">NO REAL SIEM</span></div>
				<div class="lab-intro"><div class="lab-icon" aria-hidden="true">◈</div><h3>Validate a sample scenario</h3><p>Run the illustrative rule predicate against the event displayed to the left. The check happens entirely in your browser and does not contact a server, ingest telemetry, create alerts or deploy rules.</p></div>
				<div class="expectation"><span>SCENARIO EXPECTED OUTCOME</span><strong>{chosenTest.expected}</strong></div>
				<button type="button" class="primary run" on:click={runTest}>Run synthetic detection test ↗</button>
				{#if result}
					<div class="result" class:positive={result.outcome === 'Match'} class:unknown={result.outcome === 'Insufficient telemetry'} role="status">
						<span>ILLUSTRATIVE CHECK COMPLETE</span><h3>{result.outcome}</h3><p>{result.detail}</p>
						<div class="result-compare">Expected: {chosenTest.expected} <span>·</span> Actual: {result.outcome} <span>·</span> {chosenTest.expected === result.outcome ? 'Sample expectation met' : 'Sample expectation mismatch'}</div>
					</div>
				{:else}
					<div class="result-placeholder">Choose a synthetic event and run the local predicate to see an example result.</div>
				{/if}
				<div class="lab-notes"><span class="overline">TESTING BOUNDARY</span><p>These outcomes do not measure precision, recall, ATT&CK coverage, ingestion quality or genuine protection. The future product will need real detection evaluation with independent, authorised lab telemetry.</p></div>
			</section>
		</div>
	{/if}
	<footer class="footer"><span>RH SENTRY / DETECTION ENGINEERING DESIGN</span><span>0 LIVE RULES · 0 SOURCES CONNECTED · ALL DATA SYNTHETIC</span></footer>
</div>

<style>
	.detector { color: #e9eff7; }
	.intro { display: flex; align-items: center; gap: 16px; background: linear-gradient(110deg,#23232c,#151e2a); border: 1px solid #5d4450; border-radius: 10px; padding: 19px 22px; margin-bottom: 18px; }
	.intro-icon { border: 1px solid #8b5465; color: #ffb0bf; display: grid; place-items: center; font-size: 26px; height: 46px; width: 46px; flex-shrink: 0; border-radius: 9px; }
	.intro-copy strong { font-size: 14px; }
	.intro-copy p { font-size: 12px; line-height: 1.65; color: #aab8c8; margin: 6px 0 0; }
	.intro-status { border: 1px solid #705541; color: #f0c391; padding: 10px; font-size: 10px; font-weight: 800; border-radius: 5px; margin-left: auto; flex-shrink: 0; white-space: nowrap; }
	.metrics { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 12px; }
	.metrics>div { display: flex; flex-direction: column; gap: 8px; padding: 19px; background: #111925; border: 1px solid #2b3748; border-radius: 9px; }
	.metrics span { color: #91a1b6; font-size: 10px; font-weight: 800; letter-spacing: .08em; }
	.metrics strong { font-size: 30px; line-height: 1.2; }
	.metrics small { color: #8092a7; font-size: 11px; }
	.tabs { display: flex; flex-wrap: wrap; gap: 25px; border-bottom: 1px solid #2c3746; margin: 24px 0 18px; }
	.tabs button { border: 0; border-bottom: 2px solid transparent; background: transparent; color: #98a8bb; font-weight: 750; font-size: 12px; padding: 13px 2px 15px; cursor: pointer; }
	.tabs button.active { color: #f8d6de; border-color: #e9445b; }
	.rule-grid { display: grid; grid-template-columns: minmax(280px,.85fr) minmax(440px,1.8fr); gap: 15px; align-items: start; }
	.card { background: #111924; border: 1px solid #293648; border-radius: 10px; min-width: 0; overflow: hidden; }
	.card-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 23px 22px 18px; }
	.card-heading h2 { margin: 9px 0 0; font-size: 19px; font-weight: 780; }
	.overline { font-size: 10px; color: #e06f7f; letter-spacing: .12em; font-weight: 800; }
	.count { color: #8d9db0; font-size: 10px; font-weight: 750; }
	.rule-filters { display: grid; gap: 9px; padding: 0 17px 16px; }
	.rule-filters input,.rule-filters select,.chooser-group select { color: #e2eaf4; background: #0a111b; border: 1px solid #344356; border-radius: 6px; padding: 12px; font-size: 12px; width: 100%; min-width: 0; }
	.rule-filters select option,.chooser-group select option { background: #131b28; }
	.rule-list { max-height: 700px; overflow-y: auto; }
	.rule-list button { border: 0; border-top: 1px solid #273445; background: transparent; width: 100%; color: #e4ecf5; text-align: left; padding: 18px 19px; cursor: pointer; }
	.rule-list button:hover { background: #1c2937; }
	.rule-list button.chosen { background: #30212e; box-shadow: inset 3px 0 #df4058; }
	.rule-top,.rule-foot { display: flex; justify-content: space-between; gap: 9px; }
	.rule-top { font-size: 11px; color: #9cacc0; margin-bottom: 10px; }
	.rule-top .critical { color: #fa7b91; } .rule-top .high { color: #f4b882; }
	.rule-list button strong { font-size: 13px; line-height: 1.5; display: block; }
	.rule-list button small { display: block; margin: 7px 0 11px; color: #8d9fb4; line-height: 1.55; font-size: 11px; }
	.rule-foot { color: #967d88; font-size: 10px; letter-spacing: .05em; }
	.rule-foot span:last-child { color: #e46778; }
	.demo-flag { font-size: 10px; background: #392431; border: 1px solid #724557; border-radius: 5px; padding: 8px 9px; color: #f3b4c0; white-space: nowrap; font-weight: 800; }
	.detail-hero { padding: 21px 22px; background: #1a2534; border-top: 1px solid #2d3b4c; }
	.detail-hero h3 { margin: 11px 0; font-size: 21px; line-height: 1.4; letter-spacing: -.02em; }
	.detail-hero p { color: #b3c1d2; font-size: 12px; line-height: 1.8; margin: 0; }
	.detail-fields { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 16px; padding: 23px; border-bottom: 1px solid #2a3847; }
	.detail-fields>div { display: flex; flex-direction: column; gap: 7px; }
	.detail-fields span,.source-field span { color: #8193a8; font-size: 10px; letter-spacing: .08em; font-weight: 750; }
	.detail-fields strong { color: #dae4f1; font-size: 12px; line-height: 1.5; }
	.logic { margin: 22px 23px 0; background: #0c1420; border: 1px solid #364253; border-radius: 8px; padding: 19px; }
	.logic p { font-size: 14px; color: #e6edf6; font-weight: 650; line-height: 1.7; }
	.logic small { color: #8495a8; font-size: 11px; line-height: 1.7; }
	.false-positives { margin: 22px 23px 0; }
	.false-positives ul { color: #a7b8c9; font-size: 12px; line-height: 1.8; padding-left: 19px; margin: 12px 0 0; }
	.false-positives li::marker { color: #ed6b7d; }
	.source-gap { margin: 22px 23px 0; border-left: 3px solid #c09159; background: #25252c; padding: 18px; border-radius: 5px; }
	.source-gap strong { font-size: 13px; color: #f0c491; }
	.source-gap p { font-size: 12px; color: #c8bbc0; line-height: 1.7; margin: 8px 0 12px; }
	.source-gap span { font-size: 11px; color: #e9b4a5; }
	.buttons { display: flex; gap: 9px; padding: 23px; flex-wrap: wrap; }
	.primary,.secondary,.coverage-footer button { border-radius: 7px; border: 1px solid; padding: 12px 16px; font-size: 12px; font-weight: 800; cursor: pointer; }
	.primary { background: #df3450; border-color: #ec4963; color: #fff; }
	.primary:hover { background: #f0435d; }
	.secondary { background: #1c2a38; border-color: #405068; color: #d8e4f1; }
	.secondary:hover { background: #283c50; }
	.coverage-intro { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 25px; }
	.coverage-intro h2 { font-size: 22px; margin: 10px 0; }
	.coverage-intro p { color: #a8b7c7; font-size: 12px; line-height: 1.8; max-width: 680px; margin: 0; }
	.coverage-number { min-width: 190px; display: flex; flex-direction: column; gap: 5px; align-items: center; justify-content: center; border-left: 1px solid #344356; padding-left: 25px; }
	.coverage-number strong { font-size: 53px; color: #f0c295; }
	.coverage-number small { font-size: 9px; letter-spacing: .08em; color: #9daec1; text-align: center; font-weight: 800; }
	.sources { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 14px; margin-top: 17px; }
	.source { padding: 22px; display: flex; flex-direction: column; }
	.source-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; gap: 10px; }
	.source-icon { width: 39px; height: 39px; background: #402330; border: 1px solid #784253; border-radius: 9px; color: #ffc4cf; font-size: 11px; font-weight: 800; display: grid; place-items: center; }
	.source-health { color: #efbf8e; font-size: 10px; font-weight: 750; }
	.source h3 { font-size: 17px; margin: 10px 0; }
	.source>p { color: #9eafc3; font-size: 12px; line-height: 1.7; margin: 0 0 20px; flex: 1; }
	.source-field { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
	.source-field strong { color: #d1dce8; font-size: 12px; line-height: 1.6; font-weight: 600; }
	.source-field.gap strong { color: #d8b1a4; }
	.source-footer { color: #7f91a5; font-size: 11px; padding-top: 17px; border-top: 1px solid #2c3745; margin-top: 24px; }
	.source-footer span { color: #ec677b; margin: 0 7px; }
	.coverage-footer { margin-top: 17px; padding: 22px; display: flex; justify-content: space-between; align-items: center; gap: 20px; }
	.coverage-footer h3 { margin: 10px 0; font-size: 17px; }
	.coverage-footer p { color: #a1b3c5; font-size: 12px; line-height: 1.75; margin: 0; max-width: 720px; }
	.coverage-footer button { background: #2b2130; border-color: #674151; color: #f3bcc6; flex-shrink: 0; }
	.lab-grid { display: grid; grid-template-columns: minmax(280px,.95fr) minmax(440px,1.3fr); gap: 15px; align-items: start; }
	.lab-chooser,.lab-output { padding-bottom: 22px; }
	.chooser-group { display: flex; flex-direction: column; gap: 11px; padding: 0 21px 22px; }
	.chooser-group>label,.chooser-title { color: #a0b0c2; font-size: 10px; font-weight: 800; letter-spacing: .08em; }
	.test-choice { display: flex; align-items: flex-start; gap: 12px; border: 1px solid #344253; background: #0b1320; color: #d9e3ee; border-radius: 7px; width: 100%; padding: 14px; text-align: left; cursor: pointer; }
	.test-choice.chosen { border-color: #b14b60; background: #372431; }
	.radio-mark { color: #f48193; font-size: 15px; }
	.test-choice strong { display: block; font-size: 13px; }
	.test-choice small { display: block; color: #98a9ba; font-size: 11px; line-height: 1.7; margin-top: 6px; }
	.sample-input { background: #080e16; border: 1px solid #303d4f; border-radius: 8px; margin: 0 21px; padding: 18px; }
	.sample-input pre { margin: 13px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; line-height: 1.7; color: #acc4d8; }
	.lab-intro { padding: 25px 24px 22px; text-align: center; border-top: 1px solid #2a3648; }
	.lab-icon { color: #f37488; font-size: 35px; }
	.lab-intro h3 { font-size: 20px; margin: 11px 0 8px; }
	.lab-intro p { color: #a5b5c7; font-size: 12px; line-height: 1.8; max-width: 520px; margin: 0 auto; }
	.expectation { display: flex; align-items: center; justify-content: space-between; gap: 15px; background: #182433; border: 1px solid #364458; padding: 15px 18px; margin: 0 23px 18px; border-radius: 7px; }
	.expectation span { color: #93a5b9; font-size: 10px; font-weight: 750; }
	.expectation strong { font-size: 12px; color: #e8eff8; }
	.run { display: block; margin: 0 23px 19px; width: calc(100% - 46px); }
	.result { background: #1b302e; border: 1px solid #4e7967; border-radius: 9px; padding: 20px; margin: 0 23px 21px; }
	.result.positive { background: #32242c; border-color: #9b4b62; }
	.result.unknown { background: #34302a; border-color: #a67a4b; }
	.result>span { font-size: 10px; letter-spacing: .08em; color: #c5dacc; font-weight: 800; }
	.result h3 { font-size: 24px; margin: 11px 0 8px; }
	.result p { font-size: 12px; color: #c0d1cf; line-height: 1.75; }
	.result-compare { font-size: 11px; color: #cad2d8; padding-top: 13px; border-top: 1px solid #647074; }
	.result-compare span { color: #ef7f8e; margin: 0 6px; }
	.result-placeholder { color: #8294aa; padding: 20px; margin: 0 23px; border: 1px dashed #415065; border-radius: 8px; text-align: center; font-size: 12px; line-height: 1.7; }
	.lab-notes { margin: 23px; border-top: 1px solid #304052; padding-top: 20px; }
	.lab-notes p { color: #9eb0c2; font-size: 12px; line-height: 1.75; }
	.empty { padding: 25px; font-size: 12px; color: #91a2b5; }
	.footer { display: flex; align-items: center; justify-content: space-between; gap: 14px; font-size: 10px; color: #71849b; font-weight: 750; letter-spacing: .09em; margin-top: 27px; padding-top: 19px; border-top: 1px solid #273342; }
	.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; }
	@media(max-width:1220px) { .rule-grid,.lab-grid { grid-template-columns: minmax(0,1fr); } .sources { grid-template-columns: repeat(2,minmax(0,1fr)); } }
	@media(max-width:850px) { .metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } .coverage-intro,.coverage-footer,.intro { flex-direction: column; align-items: flex-start; } .coverage-number { border-left: 0; border-top: 1px solid #344356; padding: 22px 0 0; width: 100%; } .intro-status { margin-left: 0; } }
	@media(max-width:650px) { .sources { grid-template-columns: 1fr; } .tabs { gap: 14px; } .detail-fields { grid-template-columns: 1fr; } .buttons { flex-direction: column; } .footer { flex-direction: column; align-items: flex-start; } .metrics { gap: 8px; } .metrics>div { padding: 14px; } }
</style>
