# RH Sentry — isolated Wazuh proof-of-concept plan

**Status: PREPARATION ONLY — NO WAZUH INSTALLATION OR LIVE CONNECTION.**

This document is a setup plan for the developer's **Windows / VirtualBox / 16 GB RAM** workstation. It does not imply that ChatGPT can see the user's VirtualBox settings or local machine.

## Why stage this carefully?

RH Sentry already runs as a SvelteKit preview on **127.0.0.1:5173** and a separate Python/FastAPI + SQLite training API on **127.0.0.1:8001**. Existing Wazuh-format alerts in the Event Pipeline are **fabricated**. They are not collected from a Wazuh agent, manager, indexer or customer's system.

The public SocTalk fork is not an appropriate place for company secrets, real customer events, proprietary connectors or commercially deployed source. A **private Red Horizon repository** and a reviewed credential strategy are prerequisites for a real connector.

Official documentation:
- [Wazuh VirtualBox-compatible VM installation](https://documentation.wazuh.com/current/deployment-options/virtual-machine/virtual-machine.html)
- [Wazuh quickstart hardware guidance](https://documentation.wazuh.com/current/quickstart.html)
- [Wazuh alert storage and management](https://documentation.wazuh.com/current/user-manual/manager/alert-management.html)

For **1–25 agents** the Wazuh quickstart suggests **4 vCPU, 8 GiB RAM and 50 GB disk** for an all-in-one deployment. That's a substantial portion of a 16 GB Windows laptop; **shut down Kali and any other VMs** before starting a Wazuh VM and check how much memory Windows actually has free. If the host becomes unresponsive, stop the experiment and use a different lab machine rather than overcommitting RAM.

## Stage A: offline connector validation (implemented)

Run this from the repository's \`dev\rh_sentry_lab_api\` directory with your existing Python environment:

\`\`\`powershell
.\.venv\Scripts\python.exe wazuh_replay.py --file fixtures/wazuh_training_ssh.jsonl
.\.venv\Scripts\python.exe -m pytest -q tests
\`\`\`

Expected output: a *read-only*, limited report showing **3 fictional records**, **1 training correlation**, **0 live monitoring**, **no Wazuh manager connection**, and **no database modification**.

\`wazuh_replay.py\` will only accept a small, UTF-8 JSON-lines (\`.jsonl\`) file containing manufactured test records, with \`TRAINING-\` hosts and reserved **192.0.2.0/24** test IPs. It rejects files above 256 KiB, any line above 8 KiB, more than 25 records, duplicates and malformed records. Source fields including \`full_log\`, \`previous_output\`, \`manager\` and arbitrary decoded attributes are not returned or saved. This command **never** contacts Wazuh or writes to SQLite.

Do not export real \`alerts.json\` files into this repository, pass a genuine log file to this tool, or copy customer secrets. An accidental real alert should be rejected by the training-host/IP restrictions, not treated as valid training data.

## Stage B: set up an independent VirtualBox Wazuh VM (not begun)

Only after verifying free resources and obtaining the official image:

1. Shut down the existing Kali VM (power off cleanly, do not save a state to keep consuming resources).
2. Download the current Wazuh appliance using the official Wazuh VM guide, rather than a third-party image. Confirm its version and any available integrity checks.
3. In VirtualBox choose **File → Import Appliance**, select the downloaded OVA and review CPU, RAM, disk and network settings before starting.
4. Work towards the official all-in-one baseline **4 vCPUs, 8 GiB RAM, 50 GB storage**, *only if the Windows host has enough free resources*. Do not reduce your host to unusable memory levels.
5. Use a **Host-only Adapter** for later host-to-VM testing. Avoid bridged networking, router port forwards and internet-exposed management. If downloads/updates require temporary NAT, restrict it to that purpose; no live customer data should be present.
6. Disable shared clipboard, drag-and-drop and shared folders unless a narrowly scoped transfer is explicitly required. Do not place real production credentials in snapshots or shared paths.
7. Boot Wazuh and confirm its own manager, indexer and dashboard are healthy **within the VM first**. Verify the dashboard is reachable from the Windows host *only over your intended isolated network*.
8. Follow the appliance's official initial-credential instructions, rotate passwords promptly, and keep them outside this repository, VS Code screenshots and ChatGPT. Do not suppress certificate warnings for any non-lab connection.
9. Take a clean lab snapshot **without secrets or real customer data** before adding agents or adjusting ingestion.
10. Record only non-sensitive build observations: Wazuh version, VM resources, Wazuh service health and whether host-only connectivity works. **No RH Sentry connector needs to run yet.**

No agent enrolment, automated response, attacker simulation, endpoint isolation or production port exposure is part of this step.

## Stage C: design the trusted real-telemetry boundary (NOT IMPLEMENTED)

Before any genuine lab alerts from a Wazuh manager enter RH Sentry, the next server component must have:

- A **private repository** and a non-shared development environment.
- An authenticated, source-attested collector for the Wazuh manager, **not** a public anonymous POST endpoint and not the current synthetic scenario endpoint.
- TLS, explicit identity/tenant mapping, per-tenant queue isolation, bounded ingest size/rate, durable replay protection and source acknowledgements.
- Allowlisted normalization, safe rejection/quarantine, defined retention and deletion, evidence provenance, request IDs, timestamps and operator audit.
- Redaction of credentials, usernames, paths, raw logs and any personal information not needed for a case.
- Failing-closed access controls and tests for cross-tenant leakage, replay, poisoned logs and unavailable Wazuh services.
- A deliberate distinction between **raw Wazuh alert**, **RH Sentry rule correlation**, **analyst-reviewed incident** and **unverified AI assessment**.
- No executable response actions until separately authorised, reviewed and tested.

Only after those boundaries exist should an operator send **synthetically generated alerts from the isolated lab** through a real connector. Real customers remain out of scope.

## Acceptance checklist

- [ ] Offline fictional replay passes; confirms no database writes.
- [ ] Existing RH Sentry frontend, API Lab and synthetic Event Pipeline still work.
- [ ] Python/GitHub CI security tests pass.
- [ ] Windows host memory check completed.
- [ ] Kali VM is powered off before Wazuh VM testing.
- [ ] Official Wazuh appliance imported into VirtualBox.
- [ ] Wazuh services and dashboard verified in the isolated VM.
- [ ] No public binding, bridged interface, shared credentials or customer data.
- [ ] Dedicated private repository and trusted collector plan approved before real telemetry integration.

**Cost target:** use existing Windows/VirtualBox hardware and free open-source components. No subscription or new hosting is required for these preparatory milestones, but VM performance/disk capacity may limit the laptop.
