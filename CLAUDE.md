# CLAUDE.md: Claude Code Project Guide & Multi-Agent Contract

Welcome to `ciaran-fitness-tracker`. You (**Claude Code**) are operating in a disciplined 3-agent pipeline alongside **Antigravity (AGY)** and **Gemini**.

## 1. Read First (Source of Truth)
1. `AGENTS.md` — Governance hierarchy, directory write boundaries, and 3-strike circuit breaker (`BLOCKED: CIR_BREAK`).
2. `STATE_MACHINE.md` — 5-stage autonomous transition loop (`NODE_SELECT` -> `HEADLESS_EXECUTION` -> `VERIFICATION_CYCLE` -> `SELF_HEAL` -> `AUDIT_GATE`).
3. `TASK_GRAPH.md` & `TASK_LIST.md` — Directed Acyclic Execution Graph (`G01`–`G09`) and tagged checklist.
4. `HANDOFF.md` — Current turn state, recent verification results from AGY, and your immediate action items.
5. `REQUIREMENTS.md` & `data/physio/physio-notes1.md` — Storage architecture and clinical rehabilitation constraints (02 Nov 2026 assessment).

## 2. Boundary Matrix & Tooling Rules
- **Your Write Scope (`Claude Code`)**: `backend/engine/`, `TASK_GRAPH.md`, `STATE_MACHINE.md`, plus handoff/coordination docs (`HANDOFF.md`, `TASK_LIST.md`, `REQUIREMENTS.md`).
- **AGY's Write Scope**: `frontend/`, `backend/ingestion/`, `backend/integrations/`, `backend/routers/`, `backend/tests/`, `data/processed/`.
- **Tooling Discipline**:
  - Backend: **`uv` only** (`uv run --directory backend pytest`, `uv run --directory backend ruff check`). Never raw `pip`.
  - Frontend: **`bun` only** (`bun run --cwd frontend build`, `bun test`). Never `npm`, `yarn`, or `pnpm`.
  - Issue Tracking: Sync node completions with GitHub Issues `#1`–`#6` via `gh issue`.
