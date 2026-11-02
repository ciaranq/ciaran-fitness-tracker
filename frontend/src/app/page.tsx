import { RehabPlanView } from "@/components/RehabPlanView";
import { VitalsHud } from "@/components/vitals/VitalsHud";
import rehabPlanData from "@/data/rehab-plan.json";

export default function Home() {
  const exerciseOptions = rehabPlanData.exercises.map((ex) => ({
    id: ex.id,
    name: ex.name,
  }));

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <header className="mb-8 border-b border-slate-800/80 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-cyan-800/40 bg-cyan-950/60 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-cyan-400">
            Cardio-Pulmonary &amp; Rehab Engine
          </span>
          <span className="rounded-full border border-slate-700/60 bg-slate-900/70 px-3 py-1 text-xs font-medium text-slate-300">
            Move Health Protocol
          </span>
        </div>
        <h1 className="fluid-title mt-3 font-extrabold tracking-tight text-white">
          Ciaran Fitness Tracker
        </h1>
        <p className="mt-1.5 text-sm text-slate-400 sm:text-base">
          6-Month Aerobic Baseline &amp; Adaptive Physiotherapy Progression
        </p>
      </header>

      <VitalsHud exercises={exerciseOptions} />
      <RehabPlanView />
    </main>
  );
}
