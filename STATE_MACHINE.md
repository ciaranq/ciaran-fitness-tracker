# STATE_MACHINE.md: Agent Loop Runtime Protocol

## Loop States & Autonomous Transitions
1. **NODE_SELECT** (Claude Code): Identify next `[READY]` node in `TASK_GRAPH.md`, flag `IN_PROGRESS`, emit ticket to `HANDOFF.md`.
2. **HEADLESS_EXECUTION** (AGY): Implement targeted files within directory boundaries.
3. **VERIFICATION_CYCLE** (AGY): Run `bun run build` (frontend) or `uv run pytest backend/tests/` (backend).
4. **SELF_HEAL** (AGY): If failed, inspect trace and apply scoped fix (max 3 tries before `CIR_BREAK`).
5. **AUDIT_GATE** (Claude Code): Review git diff, mark node `[COMPLETED]`, promote dependents to `[READY]`.
