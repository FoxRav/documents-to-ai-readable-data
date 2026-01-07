# INIT SESSION (paste after GLOBAL + PROJECT_CONTEXT)

**Usage:** Copy `SESSION_BOOTSTRAP_GLOBAL.md` + `PROJECT_CONTEXT.md` + this file to new chat.

Read both documents above. Treat `PROJECT_CONTEXT.md` as the **single source of truth** for project state, decisions, and constraints.

Reply with:
- **Understanding** (max 5 bullets) — what you understand about the project and task
- **Assumptions** (only if needed) — explicit assumptions you're making
- **Plan** (max 7 bullets) — how you'll approach the task
- **First patch** (minimal diff) — the smallest viable change set

**Rules:**
- Do not do broad refactors.
- Respect all "DO NOT touch" boundaries in PROJECT_CONTEXT.
- If PROJECT_CONTEXT is outdated, state your assumption explicitly.

