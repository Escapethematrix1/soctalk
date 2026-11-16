# RH Sentry — interactive design preview

**Product:** RH Sentry, Red Horizon Cyber Group's planned AI-native SOC SaaS.  
**Working branch:** `dev/rh-one` (legacy branch name; RH Sentry is a separate product from Red Horizon One).  
**Preview:** `http://127.0.0.1:5173/sentry-preview`  
**Status:** local development only. **No live security protection.**

## See the preview on Windows (PowerShell)

From your existing `RH_SOC/soctalk` folder in VS Code:

```powershell
git status --short
git pull --ff-only origin dev/rh-one
cd frontend
pnpm check
pnpm dev --host 127.0.0.1
```

If you are already in the `frontend` directory, **do not run `cd frontend` again**. If another Vite dev server is running, stop it with Ctrl+C before restarting. Keep the terminal open.

Open `http://127.0.0.1:5173/sentry-preview`. This new route intentionally bypasses the existing SocTalk sidebar, login check and backend API calls. The original pages remain untouched. If a link opens the older `/login` page instead, ensure the address ends with `/sentry-preview` and your local branch contains the latest commit.

## What to try

- Switch between Command Centre, Incidents, AI Analyst, Assets and Reports using the custom sidebar.
- Filter cases by severity and search by name/asset.
- Select a sample incident to inspect its evidence and narrative.
- Click **Inject demo alert** to add a synthetic case locally in your browser.
- Generate a sample executive briefing and click **Reset demo** to restore original sample data.

All incidents, security metrics, assets and AI confidence percentages are **fictional**; they are not fetched from a SIEM or AI service. No actual enforcement, endpoint isolation, or account changes occur. The label **DEMO ENVIRONMENT** is deliberately persistent.

## Brand and architecture safeguards

- Working brand name **RH Sentry**. No invented Red Horizon monogram/logo has been created; insert only an approved supplied logo later.
- The preview is a new isolated SvelteKit route. Existing API clients and current SocTalk dashboard remain untouched.
- A dev-only page load guard prevents navigation to this prototype in production builds. Production auth, tenancy and incident response will require separate implementation and independent testing.
- Do not connect production customer accounts or real confidential logs to this prototype.
- Some existing SocTalk routes may still show backend connection failures until its backend is configured; those failures do not affect this isolated preview.


## Stage 2 — AI Analyst workbench (added)

The **AI Analyst** section now provides:

- A searchable investigation queue with selectable sample cases.
- A preauthored investigative question, working hypothesis, benign alternative and explicit evidence gaps.
- A sample evidence register, verification steps and illustrative ATT&CK context.
- A human review screen with approve/reject decisions that update **only local Svelte component state**. They do not transmit anything, execute endpoint changes or grant real privileges.
- Case-specific run/decision state that remains while switching between RH Sentry preview sections; **Reset demo** clears it.

**These are deterministic examples, not an operational AI analyst.** No model, Wazuh ingestion, backend, real customers, alerts, agent enrollment, audit persistence or response service is connected.

### Refresh the project after this commit

If your VS Code terminal currently ends in \`...\soctalk\frontend\`, run:

\`\`\`powershell
cd ..
git pull --ff-only origin dev/rh-one
cd frontend
pnpm check
pnpm test:unit
\`\`\`

The test suite includes new RH Sentry investigation-contract tests. If \`pnpm check\` reports errors, do not proceed to integration; capture the full output for debugging.

Keep or start one Vite server with \`pnpm dev --host 127.0.0.1\`, then open \`http://127.0.0.1:5173/sentry-preview\`.



## Stage 3 — Multi-customer SaaS design (added)

The new **Customers** sidebar section shows a fictional MSSP customer portfolio:

- Searchable sample organisations and tenant-specific incident summaries.
- A toggle between an operator-facing workspace and a **visual customer-portal preview**.
- Customer-scoped *sample* incident lists and separate demonstration counts.
- Clear warning that this toggle is **not** authentication, isolation or an actual tenant boundary.
- Zero live sensors, no real customers, and no connected databases.

The AI Analyst typography and column proportions have also been adjusted for readability.

All customer names and \`.invalid\` email addresses are fabricated. A real SaaS release needs enforced server-side tenant authorisation, tested data partitioning, identity management and comprehensive audit logging. A client-side filter alone is **never** an acceptable security boundary.

The team should verify this milestone using \`pnpm check\`, \`pnpm test:unit\` and the localhost preview. This GitHub edit has **not** been executed on the developer's laptop by ChatGPT.

## Future phases (not implemented yet)

1. Refine the RH Sentry interface and approved brand assets.
2. Create typed, provider-neutral contracts for incidents, detections, assets and response approvals.
3. Connect SocTalk FastAPI to the UI, with real authentication, authorisation, tenancy and audit controls.
4. Integrate Wazuh ingestion and a tested AI investigation engine in an isolated environment.
5. Validate detection efficacy, response safety, resilience, tenant isolation, and regulatory requirements before any pilot.

The prototype is not a commercially ready SOC.
