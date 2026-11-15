# RH One — £0 VS Code development bootstrap

**Status:** planning/development only; not a live SOC service.  
**Working branch:** `dev/rh-one` in [Escapethematrix1/soctalk](https://github.com/Escapethematrix1/soctalk/tree/dev/rh-one).  
**Base project:** SocTalk (Apache 2.0; see upstream `LICENSE` and `NOTICE`). Its dependencies and Wazuh are separately licensed. Do not remove existing notices.

## Goal for the first milestone

Use Visual Studio Code to inspect, modify, and test the existing SocTalk application **without affecting the upstream main branch, exposing services, or incurring cloud costs**.

This repository contains SocTalk's existing SvelteKit frontend and Python/FastAPI backend. The Wazuh source fork is **not** needed merely to open and work on the frontend: we will use packaged Wazuh components in a separate isolated VM when testing integrations.

## A. Open the working branch in VS Code (Windows PowerShell)

If you haven't cloned SocTalk yet:

```powershell
New-Item -ItemType Directory -Force C:\RH-One | Out-Null
Set-Location C:\RH-One
git clone --branch dev/rh-one https://github.com/Escapethematrix1/soctalk.git
code .\soctalk
```

If the project is already cloned locally, open its folder in VS Code, then run in its integrated terminal:

```powershell
git status
git fetch origin
git switch dev/rh-one
```

If the final command says the branch is only available remotely, use:

```powershell
git switch --track origin/dev/rh-one
```

Before switching branches, commit or stash any existing uncommitted changes. **Never force-reset local work.**

In VS Code, use **Terminal → New Terminal** and run `git branch --show-current`. It should print `dev/rh-one`.

## B. Editor setup (no SOC deployment required)

1. Install Git for Windows if the `git` command is missing.
2. Install VS Code if not already installed.
3. In VS Code, accept the suggested workspace extensions (Svelte, Python, Pylance, Docker, GitHub Pull Requests, Remote - SSH).
4. Inspect `frontend/src` for UI code and `src/soctalk` for backend code.
5. Do not install Wazuh on your Windows host or make unnecessary modifications to its large source fork.

### Optional: verify frontend development tooling

SocTalk uses **pnpm**, not npm, for its SvelteKit frontend. Check whether Node.js and pnpm are installed:

```powershell
node --version
pnpm --version
```

If either is missing, use the current supported Node.js LTS and pnpm from their official installation instructions. Then you may run **Terminal → Run Task** in VS Code and select `RH One: Install frontend dependencies`, followed by `RH One: Frontend typecheck` or `RH One: Frontend unit tests`.

These tasks **do not deploy or start a SOC**. They may download packages to your laptop, but require no paid subscription. The project's existing lockfile is `frontend/pnpm-lock.yaml`; the install task uses `--frozen-lockfile`.

## C. Where VirtualBox fits (later)

Your current laptop has 16 GB system RAM. Keep Windows and VS Code responsive; an 8 GB Linux VM is a *starting allocation*, not a guarantee that Wazuh + SocTalk + local LLM inference can run simultaneously. Leave room for the Windows host and monitor actual RAM usage.

For our first SOC runtime test:

- Prefer **one isolated Linux test VM** with NAT networking; avoid bridged networking and public port forwards.
- Verify VM snapshots, credentials, OS patches, and host-only connectivity before running security services.
- We will integrate a packaged Wazuh installation and test SocTalk on synthetic logs.
- Introduce local Ollama/LLM inference only after the basic telemetry pipeline is stable, with a resource-appropriate small model.

**Important:** The existing root `docker-compose.yml` is described upstream as a *development/test harness only*. It publishes service ports and contains local-development credentials. Do **not** treat it as a secure production deployment. Its optional `testing` profile runs a privileged attack simulator; do not enable that without reviewing the scripts and containing the VM.

## D. Security and source-control rules

- Never put passwords, tokens, API keys, client data, live logs, or real secrets in GitHub. The project `.gitignore` already excludes `.env`, but verify what you stage before committing.
- This fork is **public**. Do not add proprietary RH One product code or internal business details here until we establish an appropriate separate private repository.
- Do not connect production accounts, Academy systems, or paying customers during the lab phase.
- Keep response actions disabled or restricted to explicitly authorised lab assets; AI-generated findings are suggestions until validated.
- Do not claim that a locally running prototype provides 24/7 managed response.
- Prefer reversible branches and small pull requests. Never overwrite upstream `main` as part of this bootstrap.

## E. Definition of done for the first milestone

- [ ] `dev/rh-one` opens in VS Code.
- [ ] Workspace extensions and language tooling recognised.
- [ ] Frontend dependencies install and checks run, with any failures recorded.
- [ ] Existing API/frontend architecture inspected.
- [ ] VirtualBox VM resource/network plan documented.
- [ ] First synthetic alert reaches the investigation workflow in an isolated lab (a separate milestone).

**Next technical decision:** whether to start the SocTalk proof of concept using its packaged demo VM or source-based developer stack. Decide after confirming the Linux VM OS, resource availability, and the current upstream release notes. No production deployment is authorised by this document.
