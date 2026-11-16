<script lang="ts">
	// RH Sentry localhost API lab UI. The backend, never the UI, authorises writes.
	type Case = {
		id: string; tenantId: string; title: string; severity: string;
		status: string; assignedTo: string | null; version: number;
	};
	type Analyst = { username: string; role: string };
	type Evidence = { id: number; actor: string; kind: string; note: string; createdAt: string };
	type History = { id: number; actor: string; action: string; detail: string; version: number; occurredAt: string };
	export let tenantId: string;
	export let incident: Case;
	export let csrf: string;
	export let canEdit: boolean;
	export let onSaved: () => Promise<void>;
	const base = 'http://127.0.0.1:8001';
	const statuses = ['triage', 'investigating', 'contained', 'closed'];
	let current: Case | null = null;
	let analysts: Analyst[] = [];
	let evidence: Evidence[] = [];
	let history: History[] = [];
	let newStatus = '';
	let newAssignee = '';
	let newNote = '';
	let busy = false;
	let loading = false;
	let message = '';
	let lastKey = '';
	let requestId = 0;
	$: key = tenantId + '/' + incident.id + '/' + incident.version + '/' + canEdit;
	$: if (key !== lastKey) {
		lastKey = key;
		void refreshCase();
	}
	$: changesPending = Boolean(current && (newStatus !== current.status || (newAssignee || null) !== current.assignedTo));

	async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
		const response = await fetch(base + path, {
			...options,
			credentials: 'include',
			cache: 'no-store',
			headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) }
		});
		if (!response.ok) {
			let detail = 'HTTP ' + response.status;
			try {
				const payload = await response.json();
				if (typeof payload.detail === 'string') detail += ': ' + payload.detail;
			} catch { /* Keep generic error. */ }
			throw new Error(detail);
		}
		return (await response.json()) as T;
	}
	function pathForCase() {
		return '/api/tenants/' + encodeURIComponent(tenantId) + '/incidents/' + encodeURIComponent(incident.id);
	}
	async function refreshCase() {
		if (!tenantId || !incident.id) return;
		const serial = ++requestId;
		loading = true;
		message = '';
		const path = pathForCase();
		try {
			const [details, analystList, notes, events] = await Promise.all([
				api<Case>(path),
				canEdit ? api<{ items: Analyst[] }>('/api/tenants/' + encodeURIComponent(tenantId) + '/analysts') : Promise.resolve({ items: [] as Analyst[] }),
				canEdit ? api<{ items: Evidence[] }>(path + '/evidence') : Promise.resolve({ items: [] as Evidence[] }),
				canEdit ? api<{ items: History[] }>(path + '/history') : Promise.resolve({ items: [] as History[] })
			]);
			if (serial !== requestId) return;
			current = details;
			analysts = analystList.items;
			evidence = notes.items;
			history = events.items;
			newStatus = details.status;
			newAssignee = details.assignedTo ?? '';
		} catch (error) {
			if (serial !== requestId) return;
			current = null;
			analysts = [];
			evidence = [];
			history = [];
			message = error instanceof Error ? error.message : 'Failed to load the example case.';
		} finally {
			if (serial === requestId) loading = false;
		}
	}
	async function updateCase() {
		if (!current || !canEdit || !changesPending || busy) return;
		busy = true;
		message = '';
		const patch: Record<string, unknown> = { expectedVersion: current.version };
		if (newStatus !== current.status) patch.status = newStatus;
		if ((newAssignee || null) !== current.assignedTo) patch.assignedTo = newAssignee || null;
		try {
			await api<Case>(pathForCase(), {
				method: 'PATCH',
				headers: { 'X-CSRF-Token': csrf },
				body: JSON.stringify(patch)
			});
			await onSaved();
			await refreshCase();
			message = 'Demo case saved in local SQLite with a versioned change record.';
		} catch (error) {
			message = error instanceof Error ? error.message : 'Case update failed.';
			if (message.includes('409')) await refreshCase();
		} finally {
			busy = false;
		}
	}
	async function addNote() {
		if (!current || !canEdit || busy || newNote.trim().length < 5) return;
		busy = true;
		message = '';
		try {
			await api<Evidence>(pathForCase() + '/evidence', {
				method: 'POST',
				headers: { 'X-CSRF-Token': csrf },
				body: JSON.stringify({ expectedVersion: current.version, note: newNote.trim() })
			});
			newNote = '';
			await onSaved();
			await refreshCase();
			message = 'Example analyst note saved locally; case version and history updated.';
		} catch (error) {
			message = error instanceof Error ? error.message : 'The note was not saved.';
			if (message.includes('409')) await refreshCase();
		} finally {
			busy = false;
		}
	}
</script>

<section class="case-panel" aria-label="Local incident management laboratory">
	<header class="head">
		<div><div class="overline">PERSISTENT CASE MANAGEMENT / LAB ONLY</div><h3>{incident.title}</h3>
			<p>{incident.id} · {tenantId} · {canEdit ? 'Analyst workflow' : 'Customer read-only view'}</p></div>
		<span class="label">SYNTHETIC RECORD</span>
	</header>
	{#if loading && !current}
		<p class="empty">Retrieving case details from the local API...</p>
	{:else if current}
		<div class="summary">
			<div><span>CASE STATE</span><strong>{current.status}</strong></div>
			<div><span>ASSIGNED ANALYST</span><strong>{current.assignedTo ?? 'Unassigned'}</strong></div>
			<div><span>RECORD VERSION</span><strong>{current.version}</strong></div>
			<div><span>SEVERITY</span><strong>{current.severity}</strong></div>
		</div>
		{#if canEdit}
			<div class="forms">
				<div class="form-card">
					<div class="overline">CASE CONTROL</div><h4>Status and assignment</h4>
					<p>All changes require a valid session, CSRF token, analyst membership and current record version.</p>
					<label for="case-status">CASE STATUS</label>
					<select id="case-status" bind:value={newStatus} disabled={busy}>
						{#each statuses as status}<option value={status}>{status}</option>{/each}
					</select>
					<label for="case-assignee">ASSIGNED ANALYST</label>
					<select id="case-assignee" bind:value={newAssignee} disabled={busy}>
						<option value="">Unassigned</option>
						{#each analysts as analyst}<option value={analyst.username}>{analyst.username} ({analyst.role})</option>{/each}
					</select>
					<button type="button" class="primary" disabled={busy || !changesPending} on:click={updateCase}>
						{busy ? 'Saving...' : 'Save incident changes'}
					</button>
					<small>Example transitions: triage → investigating → contained → closed. Invalid changes are rejected by the server.</small>
				</div>
				<div class="form-card">
					<div class="overline">EVIDENCE JOURNAL</div><h4>Add an analyst note</h4>
					<p>Plain-text notes are stored in SQLite and linked to this fictional case. No file uploads or external links.</p>
					<label for="case-note">SAMPLE INVESTIGATION NOTE</label>
					<textarea id="case-note" bind:value={newNote} disabled={busy} maxlength="1000" rows="4" placeholder="Example: Synthetic process-tree needs parent-process verification."></textarea>
					<div class="note-actions"><small>{newNote.length} / 1000 characters</small>
						<button type="button" class="primary" disabled={busy || newNote.trim().length < 5} on:click={addNote}>Save sample note</button></div>
				</div>
			</div>
			<div class="journals">
				<div class="journal">
					<div class="overline">STORED ANALYST NOTES</div><h4>Evidence register</h4>
					{#each evidence as note (note.id)}
						<div class="journal-entry"><strong>Note #{note.id} · {note.actor}</strong>
							<p>{note.note}</p><small>{note.createdAt}</small></div>
					{:else}<p class="empty">No analyst notes saved for this fictional case.</p>{/each}
				</div>
				<div class="journal">
					<div class="overline">VERSIONED CASE JOURNAL</div><h4>Change history</h4>
					{#each history as event (event.id)}
						<div class="journal-entry"><strong>{event.action} · v{event.version}</strong>
							<p>{event.detail}</p><small>{event.actor} · {event.occurredAt}</small></div>
					{:else}<p class="empty">No recorded changes to this case yet.</p>{/each}
				</div>
			</div>
		{:else}
			<div class="readonly"><strong>Read-only customer experience</strong><p>Only authorised fictional SOC analysts can change status, assign cases or access internal analyst notes. Customer viewers receive case metadata, not analyst evidence or internal history.</p></div>
		{/if}
	{:else}
		<p class="empty">Unable to load the selected case from the local API.</p>
	{/if}
	{#if message}<p class="feedback" role="status">{message}</p>{/if}
	<div class="disclaimer">RH SENTRY / DEVELOPMENT API LAB · All data is fictional and local. Not an operational SOC or production security guarantee.</div>
</section>

<style>
	.case-panel{background:#111a26;border:1px solid #324053;border-radius:11px;overflow:hidden;color:#e8eff8}
	.head{display:flex;justify-content:space-between;align-items:start;gap:15px;padding:23px;border-bottom:1px solid #303c4d}
	.head h3{font-size:20px;margin:10px 0 6px;line-height:1.4}.head p{color:#9bacc0;font-size:12px;line-height:1.7;margin:0}
	.overline{font-size:10px;font-weight:800;letter-spacing:.12em;color:#e36a7b}
	.label{border:1px solid #815065;background:#3c2734;padding:9px 10px;color:#f5c2cb;font-size:10px;font-weight:800;border-radius:5px;white-space:nowrap}
	.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding:21px}
	.summary>div{display:flex;flex-direction:column;gap:9px;border:1px solid #334254;background:#0e1622;padding:15px;border-radius:8px}
	.summary span{font-size:10px;color:#8fa2b7;letter-spacing:.06em;font-weight:800}.summary strong{font-size:14px;overflow-wrap:anywhere}
	.forms,.journals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px;padding:0 21px 20px}
	.form-card,.journal{padding:20px;background:#0d1520;border:1px solid #2d3c50;border-radius:9px;min-width:0}
	.form-card h4,.journal h4{font-size:17px;margin:10px 0}.form-card>p{font-size:12px;color:#a2b4c6;line-height:1.7;margin-bottom:19px}
	.form-card label{display:block;font-size:10px;color:#aabacc;font-weight:750;letter-spacing:.07em;margin:14px 0 8px}
	.form-card select,.form-card textarea{display:block;width:100%;background:#0a111b;color:#e7eef8;border:1px solid #38485b;border-radius:7px;padding:12px;font:12px/1.65 Inter, 'Segoe UI',Arial,sans-serif}
	.form-card select option{background:#111a26}.form-card textarea{resize:vertical}
	.primary{background:#db3951;border:1px solid #f15168;border-radius:7px;color:#fff;font-size:12px;padding:12px 15px;font-weight:800;cursor:pointer}
	.primary:disabled{opacity:.4;cursor:not-allowed}.form-card>.primary{margin-top:16px}
	.form-card small{display:block;color:#8fa0b4;font-size:11px;line-height:1.65;margin-top:12px}
	.note-actions{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-top:13px}.note-actions small{margin:0}
	.journal{max-height:320px;overflow-y:auto}.journal-entry{border-top:1px solid #2c3949;padding:15px 0}
	.journal-entry strong{font-size:12px}.journal-entry p{font-size:12px;color:#b4c2d0;line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere}.journal-entry small{color:#889aae;font-size:10px}
	.empty{color:#8ea0b5;font-size:12px;line-height:1.7;padding:14px 21px}
	.readonly{margin:0 21px 20px;padding:20px;background:#21222e;border-left:3px solid #d0a273}
	.readonly strong{font-size:13px}.readonly p{font-size:12px;color:#b8b6c2;line-height:1.75}
	.feedback{margin:0 21px 18px;color:#f4c499;background:#31272b;border:1px solid #715349;padding:14px;font-size:12px;line-height:1.6;border-radius:7px}
	.disclaimer{padding:16px 21px;background:#182433;border-top:1px solid #2f3e4e;color:#8496a9;font-size:10px;font-weight:750;letter-spacing:.07em}
	@media(max-width:1080px){.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.forms,.journals{grid-template-columns:1fr}}
	@media(max-width:650px){.head{flex-direction:column}.note-actions{flex-wrap:wrap}.summary{gap:8px;padding:12px}.summary>div{padding:11px}}
</style>
