#!/usr/bin/env python3
"""Reliable scaffolding generator and zip builder for ciaran-fitness-tracker."""
import os
import zipfile
from pathlib import Path

ROOT = Path(".")

# 1. Define folder layout
FOLDERS = [
    "data/raw/ingest",
    "data/raw/garmin/activities",
    "data/raw/garmin/metrics",
    "data/raw/garmin/user_summary",
    "data/raw/apple_health",
    "data/raw/qardio",
    "data/raw/spirometry",
    "data/raw/physio",
    "data/processed/archive",
    "data/schemas",
    "backend/ingestion",
    "backend/integrations",
    "backend/engine",
    "backend/routers",
    "backend/tests",
    "frontend/src/app",
    "frontend/src/components/vitals",
]

def write_file(path_str: str, lines: list[str]):
    p = ROOT / path_str
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")

def main():
    print("🚀 Scaffolding directory tree...")
    for folder in FOLDERS:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
        (ROOT / folder / ".gitkeep").touch()

    # --- Root Specifications ---
    write_file("AGENTS.md", [
        "# AGENTS.md: Multi-Agent Operating Contract & Tool Permissions",
        "",
        "## 1. Governance Hierarchy & Boundary Matrix",
        "| Agent | Scope | Read | Write | Permitted Tooling |",
        "| :--- | :--- | :--- | :--- | :--- |",
        "| **Claude Code** | Architect, Graph Validator, Security Reviewer | Workspace | `backend/engine/`, `TASK_GRAPH.md`, `STATE_MACHINE.md` | `bun test`, `pytest`, `ruff check`, git |",
        "| **Antigravity (AGY)** | Headless Builder, UI Developer, Test Implementer | Workspace | `frontend/`, `backend/`, `data/processed/`, `tests/` | `bun add`, `bun run dev`, `uv add`, `uvicorn`, browser tests |",
        "| **Gemini** | Spec Drafter, Context Memory, Mathematical/Domain Guide | Workspace | Spec Markdown (`AGENTS.md`, `TASK_GRAPH.md`) | None (Advisory & Spec authoring) |",
        "",
        "## 2. Hard Agent Constraints",
        "1. **No Out-of-Graph Execution**: AGY must only implement items marked `[READY]` in `TASK_GRAPH.md`.",
        "2. **Tool Discipline**: Use `bun add` (frontend) and `uv add` (backend). Never invoke npm or raw pip.",
        "3. **Circuit Breaker**: If test or build cycles fail 3 times consecutively, mark task `BLOCKED: CIR_BREAK` and halt for Claude Code review."
    ])

    write_file("TASK_GRAPH.md", [
        "# TASK_GRAPH.md: Directed Acyclic Execution Graph (DAG)",
        "",
        "## Node Registry & Status",
        "- **[COMPLETED] G01: Workspace Hardening**",
        "  - Scope: Monorepo layout, Bun runtime, UV venv, Git baseline.",
        "- **[READY] [AGY] G02: Ingest Schema Parser & Contracts**",
        "  - Depends On: G01",
        "  - Targets: `backend/ingestion/contracts.py`, `backend/tests/test_contracts.py`",
        "  - Exit Gate: `uv run pytest backend/tests/` passes.",
        "- **[READY] [AGY] G03: Frontend Skeleton & Tailwind System**",
        "  - Depends On: G01",
        "  - Targets: `frontend/src/app/`, `frontend/src/components/`",
        "  - Exit Gate: `bun run build` exits 0 with zero TypeScript errors.",
        "- **[BLOCKED] [Claude] G04: DuckDB & SQLite Layer**",
        "  - Depends On: G02",
        "  - Targets: `backend/engine/db.py`",
        "- **[BLOCKED] [AGY] G05: File Watcher Hot-Folder Loop**",
        "  - Depends On: G02",
        "  - Targets: `backend/ingestion/watcher.py`",
        "- **[BLOCKED] [Claude] G06: Periodization & Recovery Engine**",
        "  - Depends On: G04",
        "  - Targets: `backend/engine/planner.py`",
        "- **[BLOCKED] [AGY] G07: Google Workspace Bi-directional Sync**",
        "  - Depends On: G06",
        "  - Targets: `backend/integrations/google_tasks.py`, `backend/integrations/google_calendar.py`",
        "- **[BLOCKED] [AGY] G08: Glassmorphic Biometric HUD**",
        "  - Depends On: G03, G04",
        "  - Targets: `frontend/src/components/vitals/`",
        "- **[BLOCKED] [Claude + AGY] G09: End-to-End Canary Release**",
        "  - Depends On: G07, G08"
    ])

    write_file("STATE_MACHINE.md", [
        "# STATE_MACHINE.md: Agent Loop Runtime Protocol",
        "",
        "## Loop States & Autonomous Transitions",
        "1. **NODE_SELECT** (Claude Code): Identify next `[READY]` node in `TASK_GRAPH.md`, flag `IN_PROGRESS`, emit ticket to `HANDOFF.md`.",
        "2. **HEADLESS_EXECUTION** (AGY): Implement targeted files within directory boundaries.",
        "3. **VERIFICATION_CYCLE** (AGY): Run `bun run build` (frontend) or `uv run pytest backend/tests/` (backend).",
        "4. **SELF_HEAL** (AGY): If failed, inspect trace and apply scoped fix (max 3 tries before `CIR_BREAK`).",
        "5. **AUDIT_GATE** (Claude Code): Review git diff, mark node `[COMPLETED]`, promote dependents to `[READY]`."
    ])

    write_file("REQUIREMENTS.md", [
        "# REQUIREMENTS.md: Ciaran Fitness Tracker",
        "",
        "## 1. Overview",
        "Cardio-pulmonary health and fitness engine aggregating Garmin Connect, Polar HR strap, QardioArm BP, Apple Health steps, and Spirometer Peak Flow data with adaptive physio scheduling.",
        "",
        "## 2. Storage Architecture",
        "- Analytical: `biometrics.duckdb` for high-density time-series.",
        "- Operational: `app_state.db` (SQLite) for physio protocols and Google sync states.",
        "- Hot-Folder Ingest: `data/raw/ingest/` monitored by `backend/ingestion/watcher.py`."
    ])

    write_file("HANDOFF.md", [
        "# HANDOFF.md: Current Agent Execution Context",
        "",
        "## Active Target: Node G02 [Ingest Schema Engine] & Node G03 [Frontend Wire]",
        "- Assigned: Antigravity (AGY)",
        "- Verification Gates:",
        "  1. `cd frontend && bun install && bun run build` passes.",
        "  2. `cd backend && uv venv && source .venv/bin/activate && uv pip install -e . && pytest tests/` passes."
    ])

    # --- Backend Codebase ---
    write_file("backend/pyproject.toml", [
        "[project]",
        'name = "ciaran-fitness-tracker-backend"',
        'version = "0.1.0"',
        'requires-python = ">=3.12"',
        "dependencies = [",
        '    "fastapi>=0.115.0",',
        '    "uvicorn[standard]>=0.30.0",',
        '    "pydantic>=2.9.0",',
        '    "watchdog>=5.0.0",',
        '    "polars>=1.9.0",',
        '    "duckdb>=1.1.0",',
        '    "garth>=0.5.0",',
        '    "garminconnect>=0.2.16",',
        '    "fitparse>=1.2.0"',
        "]",
        "",
        "[build-system]",
        'requires = ["hatchling"]',
        'build-backend = "hatchling.build"',
        "",
        "[tool.pytest.ini_options]",
        'testpaths = ["tests"]',
        'pythonpath = ["."]'
    ])

    write_file("backend/main.py", [
        "from fastapi import FastAPI",
        "from fastapi.middleware.cors import CORSMiddleware",
        "",
        'app = FastAPI(title="Ciaran Fitness Tracker API", version="1.0.0")',
        "",
        "app.add_middleware(",
        "    CORSMiddleware,",
        '    allow_origins=["*"],',
        "    allow_credentials=True,",
        '    allow_methods=["*"],',
        '    allow_headers=["*"],',
        ")",
        "",
        '@app.get("/api/health")',
        "def health():",
        '    return {"status": "healthy", "engine": "FastAPI + UV (Python 3.12)"}',
        "",
        '@app.get("/api/v1/baseline/summary")',
        "def baseline_summary():",
        "    return {",
        '        "resting_heart_rate": 58,',
        '        "blood_pressure": {"systolic": 118, "diastolic": 76},',
        '        "peak_expiratory_flow_l_min": 520,',
        '        "phase": "Base Conditioning (Month 1)"',
        "    }"
    ])

    write_file("backend/engine/db.py", [
        "from pathlib import Path",
        "import duckdb",
        "import sqlite3",
        "",
        'PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"',
        'DUCKDB_PATH = PROCESSED_DIR / "biometrics.duckdb"',
        'SQLITE_PATH = PROCESSED_DIR / "app_state.db"',
        "",
        "def init_databases():",
        "    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)",
        "    with sqlite3.connect(SQLITE_PATH) as conn:",
        "        conn.execute('''CREATE TABLE IF NOT EXISTS physio_plans (",
        "            id TEXT PRIMARY KEY, exercise_name TEXT NOT NULL, prescribed_sets INTEGER,",
        "            prescribed_reps INTEGER, hold_seconds INTEGER, frequency_per_week INTEGER,",
        "            notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')",
        "        conn.execute('''CREATE TABLE IF NOT EXISTS sync_tracking (",
        "            id TEXT PRIMARY KEY, provider TEXT NOT NULL, external_id TEXT UNIQUE,",
        "            item_type TEXT, status TEXT, synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')",
        "        conn.commit()",
        "",
        "    con = duckdb.connect(str(DUCKDB_PATH))",
        "    con.execute('''CREATE TABLE IF NOT EXISTS vitals_log (",
        "        timestamp TIMESTAMP PRIMARY KEY, systolic_bp INTEGER, diastolic_bp INTEGER,",
        "        pulse_bpm INTEGER, resting_hr INTEGER, peak_flow_l_min INTEGER, source TEXT);''')",
        "    con.execute('''CREATE TABLE IF NOT EXISTS activity_summary (",
        "        activity_id TEXT PRIMARY KEY, start_time TIMESTAMP, activity_type TEXT,",
        "        duration_seconds DOUBLE, avg_hr INTEGER, max_hr INTEGER, zone2_seconds DOUBLE);''')",
        "    con.close()",
        "",
        'if __name__ == "__main__":',
        "    init_databases()",
        '    print("DuckDB & SQLite initialized successfully.")'
    ])

    write_file("backend/ingestion/contracts.py", [
        "from datetime import datetime",
        "from pydantic import BaseModel, Field",
        "",
        "class BloodPressureReading(BaseModel):",
        "    timestamp: datetime",
        "    systolic: int = Field(..., ge=70, le=220)",
        "    diastolic: int = Field(..., ge=40, le=140)",
        "    pulse: int = Field(..., ge=30, le=220)",
        "",
        "class SpirometryReading(BaseModel):",
        "    timestamp: datetime",
        "    peak_flow_l_min: int = Field(..., ge=100, le=900)",
        "    notes: str | None = None",
        "",
        "class ActivitySummary(BaseModel):",
        "    activity_id: str",
        "    start_time: datetime",
        "    activity_type: str",
        "    duration_seconds: float",
        "    avg_heart_rate: int | None = None",
        "    time_in_zone_2_seconds: float | None = None"
    ])

    write_file("backend/ingestion/watcher.py", [
        "import os, time",
        "from pathlib import Path",
        "from watchdog.observers import Observer",
        "from watchdog.events import FileSystemEventHandler",
        "",
        'INGEST_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "ingest"',
        "",
        "class IngestHandler(FileSystemEventHandler):",
        "    def on_created(self, event):",
        '        if not event.is_directory and not event.src_path.endswith(".gitkeep"):',
        '            print(f"[Watcher] New incoming file: {os.path.basename(event.src_path)}")',
        "",
        "def start_watching():",
        "    os.makedirs(INGEST_DIR, exist_ok=True)",
        "    observer = Observer()",
        "    observer.schedule(IngestHandler(), path=str(INGEST_DIR), recursive=False)",
        "    observer.start()",
        '    print(f"[Watcher] Monitoring {INGEST_DIR}...")',
        "    try:",
        "        while True: time.sleep(1)",
        "    except KeyboardInterrupt:",
        "        observer.stop()",
        "    observer.join()",
        "",
        'if __name__ == "__main__":',
        "    start_watching()"
    ])

    write_file("backend/tests/test_contracts.py", [
        "from datetime import datetime",
        "import pytest",
        "from ingestion.contracts import BloodPressureReading, SpirometryReading, ActivitySummary",
        "",
        "def test_blood_pressure():",
        "    r = BloodPressureReading(timestamp=datetime.now(), systolic=118, diastolic=76, pulse=58)",
        "    assert r.systolic == 118",
        "    with pytest.raises(ValueError):",
        "        BloodPressureReading(timestamp=datetime.now(), systolic=300, diastolic=76, pulse=58)",
        "",
        "def test_spirometry():",
        "    s = SpirometryReading(timestamp=datetime.now(), peak_flow_l_min=520)",
        "    assert s.peak_flow_l_min == 520",
        "",
        "def test_activity():",
        '    a = ActivitySummary(activity_id="test_1", start_time=datetime.now(), activity_type="elliptical", duration_seconds=1800.0)',
        '    assert a.activity_type == "elliptical"'
    ])

    # --- Frontend Codebase ---
    write_file("frontend/package.json", [
        "{",
        '  "name": "ciaran-fitness-tracker-frontend",',
        '  "version": "0.1.0",',
        '  "private": true,',
        '  "scripts": {',
        '    "dev": "next dev",',
        '    "build": "next build",',
        '    "start": "next start",',
        '    "lint": "next lint"',
        "  },",
        '  "dependencies": {',
        '    "clsx": "^2.1.1",',
        '    "lucide-react": "^0.453.0",',
        '    "next": "15.0.3",',
        '    "react": "^19.0.0",',
        '    "react-dom": "^19.0.0",',
        '    "tailwind-merge": "^2.5.4"',
        "  },",
        '  "devDependencies": {',
        '    "@types/node": "^22.0.0",',
        '    "@types/react": "^19.0.0",',
        '    "@types/react-dom": "^19.0.0",',
        '    "postcss": "^8.4.47",',
        '    "tailwindcss": "^3.4.14",',
        '    "typescript": "^5.6.3"',
        "  }",
        "}"
    ])

    write_file("frontend/tsconfig.json", [
        "{",
        '  "compilerOptions": {',
        '    "target": "ES2022",',
        '    "lib": ["dom", "dom.iterable", "esnext"],',
        '    "allowJs": true,',
        '    "skipLibCheck": true,',
        '    "strict": true,',
        '    "noEmit": true,',
        '    "esModuleInterop": true,',
        '    "module": "esnext",',
        '    "moduleResolution": "bundler",',
        '    "resolveJsonModule": true,',
        '    "isolatedModules": true,',
        '    "jsx": "preserve",',
        '    "incremental": true,',
        '    "plugins": [{ "name": "next" }],',
        '    "paths": { "@/*": ["./src/*"] }',
        "  },",
        '  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],',
        '  "exclude": ["node_modules"]',
        "}"
    ])

    write_file("frontend/tailwind.config.ts", [
        'import type { Config } from "tailwindcss";',
        "const config: Config = {",
        '  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],',
        "  theme: {",
        "    extend: {",
        '      colors: { background: "#080c14", surface: "rgba(15, 23, 42, 0.65)" }',
        "    }",
        "  },",
        "  plugins: [],",
        "};",
        "export default config;"
    ])

    write_file("frontend/postcss.config.mjs", [
        "const config = { plugins: { tailwindcss: {} } };",
        "export default config;"
    ])

    write_file("frontend/src/app/globals.css", [
        "@tailwind base;",
        "@tailwind components;",
        "@tailwind utilities;",
        'body { background-color: #080c14; color: #f8fafc; font-family: system-ui, sans-serif; }',
        ".glass-panel { background: rgba(18, 24, 38, 0.7); backdrop-filter: blur(14px); border: 1px solid rgba(255, 255, 255, 0.08); }"
    ])

    write_file("frontend/src/app/layout.tsx", [
        'import "./globals.css";',
        'export const metadata = { title: "Ciaran Fitness Tracker", description: "Biometric Engine" };',
        "export default function RootLayout({ children }: { children: React.ReactNode }) {",
        '  return (<html lang="en"><body className="antialiased">{children}</body></html>);',
        "}"
    ])

    write_file("frontend/src/app/page.tsx", [
        'import { HeartPulse, Activity, Wind, ShieldCheck } from "lucide-react";',
        "export default function Home() {",
        "  return (",
        '    <main className="max-w-6xl mx-auto px-6 py-12">',
        '      <header className="mb-10 border-b border-slate-800 pb-8">',
        '        <span className="text-xs uppercase font-semibold text-cyan-400 bg-cyan-950/60 px-3 py-1 rounded-full border border-cyan-800/40">Cardio-Pulmonary Engine</span>',
        '        <h1 className="text-4xl font-extrabold text-white mt-3">Ciaran Fitness Tracker</h1>',
        '        <p className="text-slate-400 mt-1 text-sm">6-Month Aerobic Baseline & Adaptive Physio Progression</p>',
        "      </header>",
        '      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">',
        '        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Resting HR</span><HeartPulse className="h-4 w-4 text-rose-400" /></div><div className="text-3xl font-bold mt-2 text-white">58 <span className="text-xs text-slate-400">bpm</span></div></div>',
        '        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Blood Pressure</span><Activity className="h-4 w-4 text-cyan-400" /></div><div className="text-3xl font-bold mt-2 text-white">118/76 <span className="text-xs text-slate-400">mmHg</span></div></div>',
        '        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Peak Flow</span><Wind className="h-4 w-4 text-emerald-400" /></div><div className="text-3xl font-bold mt-2 text-white">520 <span className="text-xs text-slate-400">L/min</span></div></div>',
        '        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Status</span><ShieldCheck className="h-4 w-4 text-amber-400" /></div><div className="text-xl font-bold mt-2 text-white">Month 1 <span className="text-xs text-slate-400">Base Build</span></div></div>',
        "      </div>",
        "    </main>",
        "  );",
        "}"
    ])

    # --- Root Configs ---
    write_file("vercel.json", [
        "{",
        '  "framework": "nextjs",',
        '  "buildCommand": "cd frontend && bun install && bun run build",',
        '  "outputDirectory": "frontend/.next"',
        "}"
    ])

    write_file(".gitignore", [
        "node_modules/",
        ".next/",
        "__pycache__/",
        "*.py[cod]",
        ".venv/",
        ".env*",
        ".DS_Store",
        "data/raw/ingest/*",
        "!data/raw/ingest/.gitkeep",
        "data/raw/garmin/*/*",
        "!data/raw/garmin/*/.gitkeep",
        "data/processed/*.duckdb",
        "data/processed/*.db"
    ])

    # --- Pack Everything Into ZIP ---
    zip_name = "ciaran-fitness-tracker-init.zip"
    print(f"📦 Packaging into {zip_name}...")
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(ROOT):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT)
                if rel_path.name in [zip_name, "init_builder.py"]:
                    continue
                zf.write(full_path, rel_path)

    print(f"✅ Success! Unpacked project files and generated {zip_name}.")

if __name__ == "__main__":
    main()
