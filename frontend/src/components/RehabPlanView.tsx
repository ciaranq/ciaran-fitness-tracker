import {
  AlertOctagon,
  Ban,
  CheckCircle2,
  Dumbbell,
  Flame,
  StretchHorizontal,
  Timer,
} from "lucide-react";
import rehabPlanData from "@/data/rehab-plan.json";

export interface RehabExercise {
  id: string;
  name: string;
  sets: number | null;
  reps: number | null;
  hold_seconds: number | null;
  notes: string | null;
  group: "strength" | "stretch";
}

export interface RehabPlan {
  assessed_on: string;
  source: string;
  exercises: RehabExercise[];
  contraindications: string[];
  stop_rule: string;
}

const plan = rehabPlanData as RehabPlan;

function formatPrescription(ex: RehabExercise): string {
  if (ex.group === "strength") {
    const sets = ex.sets ?? 3;
    const reps = ex.reps ?? 10;
    return `${sets} × ${reps} reps`;
  }
  const sets = ex.sets ?? 1;
  const hold = ex.hold_seconds ?? 30;
  return `${sets} × ${hold}s hold`;
}

export function RehabPlanView() {
  const strengthExercises = plan.exercises.filter(
    (ex) => ex.group === "strength",
  );
  const stretchExercises = plan.exercises.filter(
    (ex) => ex.group === "stretch",
  );

  return (
    <div className="space-y-10">
      {/* Prominent Stop Rule Banner */}
      <section
        aria-label="Clinical Stop Rule"
        className="rounded-2xl border border-amber-500/40 bg-gradient-to-r from-amber-950/70 via-rose-950/50 to-slate-900/80 p-5 shadow-lg shadow-amber-950/20 backdrop-blur-md"
      >
        <div className="flex items-start gap-3.5">
          <div className="mt-0.5 rounded-xl bg-amber-500/20 p-2 text-amber-300 ring-1 ring-amber-400/30">
            <AlertOctagon className="h-5 w-5 shrink-0" />
          </div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-300">
                Clinical Stop &amp; Escalation Rule
              </span>
              <span className="rounded-full border border-amber-400/30 bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-medium text-amber-200">
                Assessed {plan.assessed_on}
              </span>
            </div>
            <p className="text-sm font-medium leading-relaxed text-amber-50/95 sm:text-base">
              {plan.stop_rule}
            </p>
          </div>
        </div>
      </section>

      {/* Hard Contraindications ("Never Do" Callout) */}
      <section
        aria-labelledby="contraindications-heading"
        className="rounded-2xl border border-rose-500/35 bg-rose-950/35 p-5 backdrop-blur-md"
      >
        <header className="mb-3 flex items-center gap-2.5">
          <Ban className="h-5 w-5 text-rose-400" />
          <h2
            id="contraindications-heading"
            className="text-sm font-bold uppercase tracking-wider text-rose-300"
          >
            Never Do — Hard Contraindications
          </h2>
        </header>
        <ul className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
          {plan.contraindications.map((item) => (
            <li
              key={item}
              className="flex items-start gap-2.5 rounded-xl border border-rose-500/20 bg-slate-950/55 p-3.5 text-sm text-rose-100/90"
            >
              <span
                aria-hidden="true"
                className="mt-1 h-2 w-2 shrink-0 rounded-full bg-rose-400"
              />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Standing & Lower-Chain Strength Program (11 items) */}
      <section aria-labelledby="strength-heading" className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2.5">
            <Dumbbell className="h-5 w-5 text-cyan-400" />
            <h2
              id="strength-heading"
              className="text-xl font-bold tracking-tight text-white"
            >
              Strength Program
            </h2>
          </div>
          <span className="font-mono-metric rounded-full border border-cyan-500/30 bg-cyan-950/50 px-3 py-1 text-xs font-semibold text-cyan-300">
            {strengthExercises.length} exercises · Default 3 × 10
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {strengthExercises.map((ex, index) => {
            const isGreenBand = ex.id === "squat_green_band";
            const isProgression = ex.id === "calf_raise_single_leg";
            return (
              <article
                key={ex.id}
                data-exercise-id={ex.id}
                className="glass-panel rehab-card rounded-2xl p-5"
              >
                <header className="space-y-2">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono-metric text-xs font-semibold text-slate-400">
                        #{String(index + 1).padStart(2, "0")}
                      </span>
                      <h3 className="text-base font-bold text-white">
                        {ex.name}
                      </h3>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {isGreenBand && (
                        <span className="rounded-md border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                          Green Band
                        </span>
                      )}
                      {isProgression && (
                        <span className="rounded-md border border-violet-500/30 bg-violet-500/15 px-2 py-0.5 text-[11px] font-semibold text-violet-300">
                          Move Health Progression
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="font-mono-metric inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-cyan-500/30 bg-cyan-950/60 px-3 py-1.5 text-xs font-bold text-cyan-200">
                    <CheckCircle2 className="h-3.5 w-3.5 text-cyan-400" />
                    {formatPrescription(ex)}
                  </span>
                </header>
                {ex.notes && (
                  <p className="text-sm leading-relaxed text-slate-300">
                    {ex.notes}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </section>

      {/* Daily Asymmetric Stretching Protocol (5 items) */}
      <section aria-labelledby="stretch-heading" className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2.5">
            <StretchHorizontal className="h-5 w-5 text-emerald-400" />
            <h2
              id="stretch-heading"
              className="text-xl font-bold tracking-tight text-white"
            >
              Daily Stretching Protocol
            </h2>
          </div>
          <span className="font-mono-metric rounded-full border border-emerald-500/30 bg-emerald-950/50 px-3 py-1 text-xs font-semibold text-emerald-300">
            {stretchExercises.length} stretches · Daily (7×/wk)
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {stretchExercises.map((ex) => {
            const isPriority = ex.id === "stretch_calf_achilles_right";
            return (
              <article
                key={ex.id}
                data-exercise-id={ex.id}
                className={`glass-panel rehab-card rounded-2xl p-5 ${
                  isPriority
                    ? "border-amber-500/45 bg-gradient-to-br from-amber-950/35 to-slate-900/80 ring-1 ring-amber-400/25"
                    : ""
                }`}
              >
                <header className="space-y-2">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-bold text-white">
                        {ex.name}
                      </h3>
                      {isPriority && (
                        <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/40 bg-amber-500/20 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-amber-200">
                          <Flame className="h-3 w-3 text-amber-300" />
                          Priority
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="font-mono-metric inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-950/60 px-3 py-1.5 text-xs font-bold text-emerald-200">
                    <Timer className="h-3.5 w-3.5 text-emerald-400" />
                    {formatPrescription(ex)}
                  </span>
                </header>
                {ex.notes && (
                  <p className="text-sm leading-relaxed text-slate-300">
                    {ex.notes}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <footer className="border-t border-slate-800/80 pt-6 text-xs text-slate-400">
        <p>
          Source: {plan.source} · Total prescribed items:{" "}
          <span className="font-mono-metric font-semibold text-slate-200">
            {plan.exercises.length}
          </span>{" "}
          ({strengthExercises.length} strength + {stretchExercises.length}{" "}
          stretching)
        </p>
      </footer>
    </div>
  );
}

