# RH One — VS Code first-start guide

**Status:** initial, non-production setup. This document is for the Red Horizon development branch of SocTalk, not an assurance that the SOC has been deployed, tested or secured.

## Guardrails

- Keep the original `main` branch unchanged. Work on `dev/rh-one`.
- This fork is **public**. Never commit credentials, customer telemetry, API keys, commercial secrets, VM images or private infrastructure details here.
- Keep proprietary RH One code and private deployments in a separate **private** repository when available.
- Do not expose the demo VM, local API, Wazuh or SocTalk to the public internet. Use loopback/local-only access for the first development stage.
- Do not connect production Red Horizon or Academy systems, or real clients, until testing and authorisation are complete.
- The upstream `docker-compose.yml` explicitly says it is a **local development/test harness**, not a production deployment. Its testing profile includes a privileged attack simulator; do not start that profile casually.
- SocTalk upstream is Apache-2.0; this does not override Wazuh's or third-party licence and trademark requirements.

## 1. VS Code workspace on Windows

Install Visual Studio Code and Git for Windows if they are not already installed. In a **PowerShell** terminal:

```powershell
git --version
git clone --branch dev/rh-one https://github.com/Escapethematrix1/soctalk.git rh-one
cd rh-one
code rh-one.code-workspace
git status --short --branch
```

If you have already cloned the fork locally, **do not clone again**. Instead, open the existing folder, run `git fetch origin`, and switch to `dev/rh-one` after checking for uncommitted work.

VS Code will suggest the relevant extensions from `rh-one.code-workspace`. Open **View > Terminal** to use the integrated terminal.

## 2. Know the codebase

- `frontend/`: SvelteKit/TypeScript interface; uses pnpm (lockfile in `frontend/pnpm-lock.yaml`).
- `src/soctalk/`: Python API, security orchestration and AI logic.
- `tests/`: backend tests.
- `pyproject.toml`: requires Python >=3.11 and <3.14.
- `docker-compose.yml`: development harness, **not** a production configuration.
- `charts/`, `install.sh`: infrastructure/deployment assets, not required to edit the UI initially.
- Wazuh source is maintained separately in the user's `Escapethematrix1/wazuh` fork; **do not clone its entire source just to begin UI work**.

## 3. Optional frontend-only dependency check

This can run in VS Code before the VirtualBox stage. It requires a locally installed modern Node.js and pnpm/Corepack. From the repo root:

```powershell
cd frontend
node --version
corepack pnpm --version
corepack pnpm install --frozen-lockfile
corepack pnpm check
corepack pnpm test:unit
```

Do **not** assume the application will work end-to-end from these commands: most dashboard features require the API/database/SIEM environment. Record any errors for review. These commands are instructions, **not completed test results**.

If Node.js or Corepack is absent, leave this step until the local tooling is installed. Do not install dependencies from unfamiliar packages outside the verified repository.

## 4. VirtualBox comes next

The laptop has 16 GB physical RAM. The upstream SocTalk demo suggests 4 vCPUs, 8 GB RAM and at least 60 GB disk for its VM; those settings may leave Windows short of memory during a full-stack + local-LLM run. First verify available RAM, CPU virtualisation and disk space. Run only the SOC core initially; assess lightweight/local AI in a later step.

Before connecting the VM to anything, verify its OS version, network mode, listening ports, user credentials, and snapshot/backup state. A prebuilt demo appliance is **not** a secure production deployment.

## 5. First milestone: measurable demo

A useful milestone is not simply a branded page. The milestone passes only when:
1. An isolated Wazuh instance receives a safe synthetic event.
2. A detection surfaces it in the SOC.
3. SocTalk creates or updates an investigation with cited evidence.
4. The analyst can view and review the case locally.
5. No customer/production systems are touched and no secrets are pushed to GitHub.

## Next work items

- Confirm VS Code opens `rh-one.code-workspace` on the `dev/rh-one` branch.
- Determine whether the frontend's dependency checks pass locally.
- Inspect and size the existing VirtualBox Linux machine.
- Review local-demo authentication and credentials before running services.
- Set up a separate private repository for RH One proprietary code and deployment configuration.
- Baseline existing SOC functionality *before* changing branding or core detection logic.
