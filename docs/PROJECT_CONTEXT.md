# PROJECT CONTEXT (single source of truth)

**Purpose:** Project-specific state, decisions, and constraints. Update when:
- Major decision made (DB/architecture/API)
- New dependency or tooling added
- DoD/acceptance criteria changed
- New known issue or regression found
- Milestone/sprint completed

**Last updated:** <YYYY-MM-DD>

## 1) Project summary (what we're building)
**Product / repo name:** <NAME>
**One-line goal:** <WHAT IT DOES>
**Primary users:** <WHO>
**Core use-case(s):** <BULLETS>
**Non-goals:** <BULLETS>

## 2) Current state
**Repo link / path:** <URL or local path>
**What works today:** <BULLETS>
**What's broken / missing:** <BULLETS>
**Known constraints:** <BUDGET, LATENCY, SECURITY, COMPLIANCE>

## 3) Tech stack & environment (authoritative)
**Language(s):** <e.g., Python 3.12, TS 5.x>
**Frameworks:** <FastAPI, Next.js, etc>
**Runtime:** <Docker, k8s, serverless, bare metal>
**DB / storage:** <Postgres, S3, etc>
**Auth:** <Keycloak/OAuth/etc>
**CI/CD:** <GitHub Actions/etc>
**OS/dev env:** <Windows 11 / Linux>
**Package manager:** <pip/poetry/pnpm/etc>
**Lint/format:** <ruff/black/eslint/prettier/etc>
**Tests:** <pytest/jest/etc>

## 4) Repo structure & editing boundaries
**Key folders:**  
- <src/> = application code  
- <scripts/> = utilities  
- <docs/> = docs  
- <infra/> = deployment  
**DO NOT touch:** <FILES/FOLDERS>
**Allowed to add new files:** yes/no

## 7) Definition of Done (acceptance criteria)
- Functional: <BULLETS>
- Performance: <latency/throughput targets>
- Security: <threat model items>
- Reliability: <retry/backoff, idempotency, etc>
- Observability: <metrics/logs/traces>
- Docs: <what must be documented>

## 8) Test & regression anchors
**Must-pass tests:** <list>
**Golden queries / fixtures:** <list>
**Manual smoke steps:** <list>

## 9) Decision log (keep brief)
Record major decisions with date + rationale:
- <YYYY-MM-DD> <decision> — <why>

