# AGENTS.md: Multi-Agent Operating Contract & Tool Permissions

## 1. Governance Hierarchy & Boundary Matrix
| Agent | Scope | Read | Write | Permitted Tooling |
| :--- | :--- | :--- | :--- | :--- |
| **Claude Code** | Architect, Graph Validator, Security Reviewer | Workspace | `backend/engine/`, `TASK_GRAPH.md`, `STATE_MACHINE.md` | `bun test`, `pytest`, `ruff check`, git |
| **Antigravity (AGY)** | Headless Builder, UI Developer, Test Implementer | Workspace | `frontend/`, `backend/`, `data/processed/`, `tests/` | `bun add`, `bun run dev`, `uv add`, `uvicorn`, browser tests |
| **Gemini** | Spec Drafter, Context Memory, Mathematical/Domain Guide | Workspace | Spec Markdown (`AGENTS.md`, `TASK_GRAPH.md`) | None (Advisory & Spec authoring) |

## 2. Hard Agent Constraints
1. **No Out-of-Graph Execution**: AGY must only implement items marked `[READY]` in `TASK_GRAPH.md`.
2. **Tool Discipline**: Use `bun add` (frontend) and `uv add` (backend). Never invoke npm or raw pip.
3. **Circuit Breaker**: If test or build cycles fail 3 times consecutively, mark task `BLOCKED: CIR_BREAK` and halt for Claude Code review.
