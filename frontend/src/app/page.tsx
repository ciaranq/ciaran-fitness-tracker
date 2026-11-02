import { HeartPulse, Activity, Wind, ShieldCheck } from "lucide-react";
export default function Home() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-12">
      <header className="mb-10 border-b border-slate-800 pb-8">
        <span className="text-xs uppercase font-semibold text-cyan-400 bg-cyan-950/60 px-3 py-1 rounded-full border border-cyan-800/40">Cardio-Pulmonary Engine</span>
        <h1 className="text-4xl font-extrabold text-white mt-3">Ciaran Fitness Tracker</h1>
        <p className="text-slate-400 mt-1 text-sm">6-Month Aerobic Baseline & Adaptive Physio Progression</p>
      </header>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Resting HR</span><HeartPulse className="h-4 w-4 text-rose-400" /></div><div className="text-3xl font-bold mt-2 text-white">-- <span className="text-xs text-slate-400">bpm</span></div></div>
        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Blood Pressure</span><Activity className="h-4 w-4 text-cyan-400" /></div><div className="text-3xl font-bold mt-2 text-white">--/-- <span className="text-xs text-slate-400">mmHg</span></div></div>
        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Peak Flow</span><Wind className="h-4 w-4 text-emerald-400" /></div><div className="text-3xl font-bold mt-2 text-white">--- <span className="text-xs text-slate-400">L/min</span></div></div>
        <div className="glass-panel p-5 rounded-2xl"><div className="flex justify-between text-slate-400"><span className="text-xs uppercase font-medium">Status</span><ShieldCheck className="h-4 w-4 text-amber-400" /></div><div className="text-xl font-bold mt-2 text-white">Month 1 <span className="text-xs text-slate-400">Base Build</span></div></div>
      </div>
    </main>
  );
}
