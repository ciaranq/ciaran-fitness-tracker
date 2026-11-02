"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CalendarRange,
  CheckCircle2,
  HeartPulse,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Wind,
} from "lucide-react";

interface BaselineSummary {
  resting_heart_rate: number | null;
  blood_pressure: { systolic: number | null; diastolic: number | null } | null;
  peak_expiratory_flow_l_min: number | null;
  baseline_zone2_minutes: number | null;
  phase: string;
}

interface WeeklyTarget {
  week: number;
  zone2_minutes: number;
  strength_sessions: number;
  deload: boolean;
  held: boolean;
  hold_reasons: string[];
}

interface PeriodizationPlan {
  baseline_minutes: number;
  hold_reasons: string[];
  weeks: WeeklyTarget[];
}

interface ProgressionSuggestion {
  exercise_id: string;
  suggestion: string;
  clean_sessions: number;
  message: string;
}

interface FlareDecision {
  state: "CLEAR" | "STOP_AND_REVIEW";
  halted_exercise_ids: string[];
  reasons: string[];
  message: string;
}

interface RehabApiState {
  progression_suggestions: ProgressionSuggestion[];
  flare_decision: FlareDecision;
}

interface ExerciseOption {
  id: string;
  name: string;
}

const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export function VitalsHud({ exercises }: { exercises: ExerciseOption[] }) {
  const [summary, setSummary] = useState<BaselineSummary | null>(null);
  const [periodization, setPeriodization] = useState<PeriodizationPlan | null>(
    null,
  );
  const [rehabState, setRehabState] = useState<RehabApiState | null>(null);
  const [apiStatus, setApiStatus] = useState<
    "static" | "connecting" | "connected" | "offline"
  >("static");

  const [selectedExercise, setSelectedExercise] = useState<string>(
    exercises[0]?.id ?? "squat_green_band",
  );
  const [selectedSymptom, setSelectedSymptom] = useState<string>("");
  const [sessionSubmitting, setSessionSubmitting] = useState(false);

  const syncWithBackend = useCallback(async (baseUrl: string) => {
    const targetBase = baseUrl || "http://127.0.0.1:8000";
    setApiStatus("connecting");
    try {
      const [sumRes, rehabRes, perRes] = await Promise.all([
        fetch(`${targetBase}/api/v1/baseline/summary`),
        fetch(`${targetBase}/api/v1/plan/rehab`),
        fetch(`${targetBase}/api/v1/plan/periodization`),
      ]);

      if (!sumRes.ok || !rehabRes.ok) {
        setApiStatus("offline");
        return;
      }

      const sumData = (await sumRes.json()) as BaselineSummary;
      const rehabData = (await rehabRes.json()) as RehabApiState;
      setSummary(sumData);
      setRehabState(rehabData);

      if (perRes.ok) {
        const perData = (await perRes.json()) as PeriodizationPlan;
        setPeriodization(perData);
      } else {
        setPeriodization(null);
      }
      setApiStatus("connected");
    } catch {
      setApiStatus("offline");
    }
  }, []);

  useEffect(() => {
    if (DEFAULT_API_BASE) {
      void syncWithBackend(DEFAULT_API_BASE);
    }
  }, [syncWithBackend]);

  const handleLogSession = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetBase = DEFAULT_API_BASE || "http://127.0.0.1:8000";
    setSessionSubmitting(true);
    try {
      const res = await fetch(`${targetBase}/api/v1/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          exercise_id: selectedExercise,
          symptom: selectedSymptom || null,
        }),
      });
      if (res.ok) {
        await syncWithBackend(targetBase);
      }
    } catch {
      setApiStatus("offline");
    } finally {
      setSessionSubmitting(false);
    }
  };

  const rhrDisplay =
    summary?.resting_heart_rate != null
      ? String(summary.resting_heart_rate)
      : "--";
  const bpDisplay =
    summary?.blood_pressure?.systolic != null &&
    summary?.blood_pressure?.diastolic != null
      ? `${summary.blood_pressure.systolic}/${summary.blood_pressure.diastolic}`
      : "--/--";
  const pefDisplay =
    summary?.peak_expiratory_flow_l_min != null
      ? String(summary.peak_expiratory_flow_l_min)
      : "---";
  const phaseDisplay = summary?.phase ?? "Month 1";

  return (
    <section aria-label="Biometric Vitals & Live Telemetry HUD" className="mb-10 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span
            className={`h-2 w-2 rounded-full ${
              apiStatus === "connected"
                ? "bg-emerald-400"
                : apiStatus === "connecting"
                  ? "animate-pulse bg-amber-400"
                  : "bg-slate-500"
            }`}
          />
          <span>
            {apiStatus === "connected"
              ? "Live FastAPI Telemetry Connected"
              : apiStatus === "offline"
                ? "Local FastAPI Offline — Showing Public-Safe Placeholders"
                : "Public-Safe Mode (Static Plan View)"}
          </span>
        </div>
        <button
          type="button"
          onClick={() => void syncWithBackend(DEFAULT_API_BASE)}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700/80 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/50 hover:text-cyan-300"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${
              apiStatus === "connecting" ? "animate-spin" : ""
            }`}
          />
          Sync Local Engine
        </button>
      </div>

      {/* 4 Core Biometric Vitals Cards */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <article className="glass-panel rehab-card rounded-2xl p-4 sm:p-5">
          <header className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">
              Resting HR
            </span>
            <HeartPulse className="h-4 w-4 text-rose-400" />
          </header>
          <p className="font-mono-metric mt-1 text-2xl font-bold text-white sm:text-3xl">
            {rhrDisplay}{" "}
            <span className="text-xs font-normal text-slate-400">bpm</span>
          </p>
        </article>

        <article className="glass-panel rehab-card rounded-2xl p-4 sm:p-5">
          <header className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">
              Blood Pressure
            </span>
            <Activity className="h-4 w-4 text-cyan-400" />
          </header>
          <p className="font-mono-metric mt-1 text-2xl font-bold text-white sm:text-3xl">
            {bpDisplay}{" "}
            <span className="text-xs font-normal text-slate-400">mmHg</span>
          </p>
        </article>

        <article className="glass-panel rehab-card rounded-2xl p-4 sm:p-5">
          <header className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">
              Peak Flow
            </span>
            <Wind className="h-4 w-4 text-emerald-400" />
          </header>
          <p className="font-mono-metric mt-1 text-2xl font-bold text-white sm:text-3xl">
            {pefDisplay}{" "}
            <span className="text-xs font-normal text-slate-400">L/min</span>
          </p>
        </article>

        <article className="glass-panel rehab-card rounded-2xl p-4 sm:p-5">
          <header className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium uppercase tracking-wider">
              Phase Status
            </span>
            <ShieldCheck className="h-4 w-4 text-amber-400" />
          </header>
          <p className="mt-1 text-lg font-bold text-white sm:text-xl">
            {phaseDisplay}{" "}
            {!summary && (
              <span className="text-xs font-normal text-slate-400">
                Base Build
              </span>
            )}
          </p>
        </article>
      </div>

      {/* Live Engine Panels (Rendered when local FastAPI is synced) */}
      {apiStatus === "connected" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Session Logger & Flare Circuit Breaker */}
          <article className="glass-panel rehab-card rounded-2xl p-5">
            <header className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-cyan-300">
                Log Rehab Session &amp; Symptom Gate
              </h2>
              <CheckCircle2 className="h-4 w-4 text-cyan-400" />
            </header>

            <form onSubmit={handleLogSession} className="space-y-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="block space-y-1 text-xs text-slate-300">
                  <span>Exercise</span>
                  <select
                    value={selectedExercise}
                    onChange={(e) => setSelectedExercise(e.target.value)}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3 py-2 text-xs text-white"
                  >
                    {exercises.map((ex) => (
                      <option key={ex.id} value={ex.id}>
                        {ex.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block space-y-1 text-xs text-slate-300">
                  <span>Symptom Check</span>
                  <select
                    value={selectedSymptom}
                    onChange={(e) => setSelectedSymptom(e.target.value)}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3 py-2 text-xs text-white"
                  >
                    <option value="">None (Clean Session)</option>
                    <option value="posterior_right_knee">
                      Posterior right knee stiffness/pain
                    </option>
                    <option value="left_sciatic_radiation">
                      Left glute / sciatic radiation
                    </option>
                    <option value="shoulder_pain">Shoulder pain</option>
                  </select>
                </label>
              </div>

              <button
                type="submit"
                disabled={sessionSubmitting}
                className="rounded-xl bg-cyan-500/20 px-4 py-2 text-xs font-bold text-cyan-200 ring-1 ring-cyan-400/40 transition hover:bg-cyan-500/30 disabled:opacity-50"
              >
                {sessionSubmitting ? "Recording..." : "Record Session"}
              </button>
            </form>

            {rehabState?.flare_decision.state === "STOP_AND_REVIEW" && (
              <div className="rounded-xl border border-rose-500/50 bg-rose-950/60 p-3.5 text-xs text-rose-100">
                <div className="flex items-center gap-2 font-bold text-rose-300">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>STOP_AND_REVIEW Circuit Breaker Active</span>
                </div>
                <p className="mt-1">{rehabState.flare_decision.message}</p>
                <ul className="mt-1.5 list-inside list-disc text-rose-200/90">
                  {rehabState.flare_decision.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {rehabState && rehabState.progression_suggestions.length > 0 && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-3.5 text-xs text-emerald-100">
                <div className="flex items-center gap-1.5 font-bold text-emerald-300">
                  <Sparkles className="h-4 w-4" />
                  <span>Clinician Progression Suggestions (6+ Clean Sessions)</span>
                </div>
                <ul className="mt-1.5 space-y-1">
                  {rehabState.progression_suggestions.map((s) => (
                    <li key={s.exercise_id}>{s.message}</li>
                  ))}
                </ul>
              </div>
            )}
          </article>

          {/* 26-Week Zone 2 Periodization Summary */}
          <article className="glass-panel rehab-card rounded-2xl p-5">
            <header className="flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-emerald-300">
                26-Week Zone 2 Periodization
              </h2>
              <CalendarRange className="h-4 w-4 text-emerald-400" />
            </header>

            {periodization ? (
              <div className="space-y-3 text-xs text-slate-300">
                <p>
                  28-Day Zone 2 Baseline:{" "}
                  <span className="font-mono-metric font-bold text-white">
                    {periodization.baseline_minutes.toFixed(1)} min/wk
                  </span>
                </p>
                {periodization.hold_reasons.length > 0 && (
                  <div className="rounded-xl border border-amber-500/40 bg-amber-950/40 p-2.5 text-amber-200">
                    <strong>Week 1 Vitals Hold:</strong>{" "}
                    {periodization.hold_reasons.join(" ")}
                  </div>
                )}
                <div className="grid grid-cols-4 gap-2">
                  {periodization.weeks.slice(0, 4).map((w) => (
                    <div
                      key={w.week}
                      className="rounded-xl border border-slate-800 bg-slate-950/60 p-2.5"
                    >
                      <div className="text-[11px] text-slate-400">
                        Wk {w.week} {w.deload ? "(Deload)" : w.held ? "(Hold)" : ""}
                      </div>
                      <div className="font-mono-metric mt-0.5 text-sm font-bold text-white">
                        {w.zone2_minutes}m
                      </div>
                      <div className="text-[10px] text-cyan-300">
                        {w.strength_sessions}× strength
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs leading-relaxed text-slate-400">
                No Zone 2 activity baseline in DuckDB yet. Drop Garmin{" "}
                <code className="text-cyan-300">.json</code> or{" "}
                <code className="text-cyan-300">.csv</code> summaries into{" "}
                <code className="text-cyan-300">data/raw/ingest/</code> to
                generate the 26-week ramp.
              </p>
            )}
          </article>
        </div>
      )}
    </section>
  );
}

