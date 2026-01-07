# Session Bootstrap Documentation

2-tier prompt system for consistent AI-assisted development.

## Structure

### 1. `SESSION_BOOTSTRAP_GLOBAL.md` (rarely changes)
**Purpose:** Reusable working rules and response format.
**Contains:** Role, coding standards, output contract, first action rules.
**Update when:** Your general working preferences change.

### 2. `PROJECT_CONTEXT.md` (living document)
**Purpose:** Single source of truth for project state, decisions, and constraints.
**Contains:** Project summary, current state, tech stack, repo structure, DoD, tests, decision log.
**Update when:**
- Major decision made (DB/architecture/API)
- New dependency or tooling added
- DoD/acceptance criteria changed
- New known issue or regression found
- Milestone/sprint completed

### 3. `INIT_SESSION.md` (usage instructions)
**Purpose:** Instructions for starting a new chat session.
**Usage:** Copy GLOBAL + PROJECT_CONTEXT + this file to new chat.

### 4. `RESET_PROMPT.md` (recovery)
**Purpose:** Reset assistant when it goes off-rails.
**Usage:** Paste when assistant needs to refocus on minimal diffs.

## Usage Workflow

1. **New project:** Copy `PROJECT_CONTEXT.md` and fill in sections 1-4, 7-9.
2. **New chat:** Copy `SESSION_BOOTSTRAP_GLOBAL.md` + `PROJECT_CONTEXT.md` + `INIT_SESSION.md`.
3. **During work:** Update `PROJECT_CONTEXT.md` when major changes occur (see update triggers above).
4. **If stuck:** Use `RESET_PROMPT.md` to refocus.

## File Encoding

All files are UTF-8 with BOM for Windows compatibility.

