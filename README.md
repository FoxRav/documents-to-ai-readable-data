# Cursor Helper Pack Template

This repository is a template that ships a reusable **assistant-pack** (prompt and workflow rules) alongside a separate **workspace** where you build actual software projects.

## Why this exists
LLM output can vary between chats. The assistant-pack standardizes:
- role and working rules (no guessing, minimal diffs)
- required response structure (understanding → plan → changes → verification → risks)
- a reset mechanism when the model goes off-rails
- a project context template that evolves as the project evolves

## Repo layout
- `assistant-pack/` — reusable prompt toolkit (kept stable, versioned)
- `workspace/` — your actual projects live here (outside the assistant-pack)

## Quick start (new project)
1. Create a new folder in `workspace/`, e.g. `workspace/my-app/`
2. Copy `assistant-pack/PROJECT_CONTEXT_TEMPLATE.md` into `workspace/my-app/PROJECT_CONTEXT.md` and fill it.
3. Start a new Cursor chat and paste:
   - `assistant-pack/SESSION_BOOTSTRAP_GLOBAL.md`
   - `workspace/my-app/PROJECT_CONTEXT.md`
   - `assistant-pack/INIT_SESSION.md`
4. Then paste your task.

## When the model goes off-rails
Paste `assistant-pack/RESET_PROMPT.md` to force a minimal diff + verification.

## Encoding requirement
All markdown files in `assistant-pack/` are stored as **UTF-8 with BOM**.

