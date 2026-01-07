# Prompt Pack: Global Bootstrap + Project Context + Init + Reset

## What this is
This prompt pack reduces "random developer" variance by enforcing:
- no guessing (explicit assumptions or one clarifying question)
- minimal diffs and small, reviewable changes
- a fixed response contract (understanding → plan → changes → verification → risks)
- a reset mechanism when the assistant drifts into refactors or scope creep

## Two-layer model (recommended)
### 1) Global layer (stable)
`SESSION_BOOTSTRAP_GLOBAL.md` is reusable across projects and changes rarely.

### 2) Project layer (living document)
Each project has its own `PROJECT_CONTEXT.md` (copied from the template) and evolves as the project evolves.

Do not "pollute" the global bootstrap with project-specific details.

## Update cadence (event-driven, not prompt-count driven)
Update `PROJECT_CONTEXT.md` when any of these happens:
- architecture / technology decision
- Definition of Done changes
- new dependency, tooling, lint, tests, CI/CD change
- a new known bug, limitation, or regression anchor
- milestone / release completion

## New chat workflow (recommended paste order)
1) `assistant-pack/SESSION_BOOTSTRAP_GLOBAL.md`
2) `<project>/PROJECT_CONTEXT.md`
3) `assistant-pack/INIT_SESSION.md`
Then paste the task.

## Reset workflow
When the assistant proposes unnecessary refactors, breaks interfaces, guesses, or skips verification:
Paste `assistant-pack/RESET_PROMPT.md`.

## Do / Don't
### DO
- require a plan before code
- require minimal diffs
- require verification commands + expected outcome
- keep "DO NOT touch" boundaries explicit

### DON'T
- do broad refactors unless explicitly requested
- change interfaces without approval
- accept code without verification steps

