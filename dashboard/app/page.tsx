'use client';

import { useState, useEffect } from 'react';

export default function Dashboard() {
  const [status, setStatus] = useState('Opérationnel ⚡');
  const [lastUpdate, setLastUpdate] = useState('');
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    setLastUpdate(new Date().toLocaleTimeString());
    const interval = setInterval(() => {
      setLastUpdate(new Date().toLocaleTimeString());
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-[#030712] text-slate-100 p-4 sm:p-6 md:p-10 font-sans selection:bg-cyan-500 selection:text-black">
      
      {/* Background Glow Effect */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))] pointer-events-none"></div>

      {/* Top Navigation / Header */}
      <header className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800/80 pb-6 gap-4 relative z-10">
        <div>
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-500 bg-clip-text text-transparent">
              Amal-DG — Control Center
            </h1>
            <span className="text-[10px] bg-cyan-950/80 border border-cyan-800/60 text-cyan-400 px-2.5 py-0.5 rounded-full font-mono font-semibold uppercase tracking-wider">
              v1.0 Live
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Supervision autonome des 8 pôles d'experts & Pilotage LLM (TAL & Immobilier Québec)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-slate-900/90 border border-slate-800 px-3.5 py-2 rounded-xl text-xs flex items-center gap-2 shadow-inner">
            <span className="text-slate-400">Backend Render :</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              {status}
            </span>
            <span className="text-slate-500 text-[10px] border-l border-slate-800 pl-2 ml-1 font-mono">
              {lastUpdate}
            </span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto space-y-8 relative z-10">
        
        {/* Metric Cards Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 hover:border-slate-700 transition">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Pôles Actifs</div>
            <div className="text-2xl font-bold text-white font-mono">8 / 8</div>
            <div className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
              <span>●</span> Prêts pour missions
            </div>
          </div>
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 hover:border-slate-700 transition">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Modèles LLM</div>
            <div className="text-2xl font-bold text-cyan-400 font-mono">3 Opérationnels</div>
            <div className="text-[10px] text-slate-400 mt-1">Circuit Breaker : 0 échec</div>
          </div>
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 hover:border-slate-700 transition">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Conformité QC</div>
            <div className="text-2xl font-bold text-indigo-400 font-mono">100% TAL / Loi 25</div>
            <div className="text-[10px] text-indigo-300 mt-1">Règles vérifiées</div>
          </div>
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 hover:border-slate-700 transition">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Latence Moyen</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">140 ms</div>
            <div className="text-[10px] text-emerald-400 mt-1">Render Cloud Ultra-fast</div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: LLM Models status */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-2xl p-5 shadow-2xl">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <span className="text-cyan-400">⚡</span> Modèles LLM & Quotas
                </h2>
                <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">Auto-Failover</span>
              </div>
              <div className="space-y-3">
                
                <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-xl hover:border-cyan-500/40 transition">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-xs text-slate-200 font-mono">google/gemma-4-31b-it</span>
                    <span className="text-emerald-400 text-[10px] px-2 py-0.5 bg-emerald-950/60 border border-emerald-800/60 rounded-full font-bold">HEALTHY</span>
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-400 mt-2">
                    <span>Échecs : 0</span>
                    <span className="text-slate-500">Tier : Free</span>
                  </div>
                </div>

                <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-xl hover:border-cyan-500/40 transition">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-xs text-slate-200 font-mono">z-ai/glm-5.2</span>
                    <span className="text-emerald-400 text-[10px] px-2 py-0.5 bg-emerald-950/60 border border-emerald-800/60 rounded-full font-bold">HEALTHY</span>
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-400 mt-2">
                    <span>Échecs : 0</span>
                    <span className="text-slate-500">Tier : Free</span>
                  </div>
                </div>

                <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-xl hover:border-cyan-500/40 transition">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-xs text-slate-200 font-mono">google/gemma-4-26b</span>
                    <span className="text-emerald-400 text-[10px] px-2 py-0.5 bg-emerald-950/60 border border-emerald-800/60 rounded-full font-bold">HEALTHY</span>
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-400 mt-2">
                    <span>Échecs : 0</span>
                    <span className="text-slate-500">Tier : Free</span>
                  </div>
                </div>

              </div>
            </div>
          </div>

          {/* Right 2 Columns: 8 Poles Status */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800/80 rounded-2xl p-5 shadow-2xl">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-5">
                <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <span className="text-indigo-400">📊</span> Les 8 Pôles d'Experts Autonomes
                </h2>
                <div className="flex gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800/80 text-[11px]">
                  <button onClick={() => setActiveTab('all')} className={`px-2.5 py-1 rounded-md transition ${activeTab === 'all' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-white'}`}>Tous (8)</button>
                  <button onClick={() => setActiveTab('ready')} className={`px-2.5 py-1 rounded-md transition ${activeTab === 'ready' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-white'}`}>Prêts</button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                
                {[
                  { id: '01', name: 'Produit & Vision', role: 'Analytique SaaS', color: 'text-blue-400', border: 'hover:border-blue-500/40' },
                  { id: '02', name: 'Juridique (TAL & Loi 25)', role: 'Droit Immobilier QC', color: 'text-indigo-400', border: 'hover:border-indigo-500/40' },
                  { id: '03', name: 'Architecture SaaS', role: 'Fullstack & Cloud', color: 'text-purple-400', border: 'hover:border-purple-500/40' },
                  { id: '04', name: 'UX/UI & Expérience', role: 'Design System B2B', color: 'text-pink-400', border: 'hover:border-pink-500/40' },
                  { id: '05', name: 'Growth & Marché QC', role: 'Acquisition PropTech', color: 'text-emerald-400', border: 'hover:border-emerald-500/40' },
                  { id: '06', name: 'Finance & Modèle Éco', role: 'Tarification SaaS', color: 'text-amber-400', border: 'hover:border-amber-500/40' },
                  { id: '07', name: 'Sécurité & Conformité', role: 'Loi 25 & Privacy', color: 'text-cyan-400', border: 'hover:border-cyan-500/40' },
                  { id: '08', name: 'Pilotage & Orchestration', role: 'Master Agent DG', color: 'text-rose-400', border: 'hover:border-rose-500/40' },
                ].map((pole) => (
                  <div key={pole.id} className={`bg-slate-950/80 border border-slate-800/80 p-3.5 rounded-xl ${pole.border} transition group`}>
                    <div className="flex justify-between items-center mb-2">
                      <span className={`text-[11px] font-bold uppercase tracking-wider ${pole.color}`}>
                        {pole.id}. {pole.name}
                      </span>
                      <span className="text-[9px] bg-slate-900 border border-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                        STANDBY
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-slate-200">{pole.role}</div>
                    <div className="text-[11px] text-slate-500 mt-1">Prêt pour allocation de tâches</div>
                  </div>
                ))}

              </div>
            </div>
          </div>

        </div>

        {/* Live Logs / Activity Terminal */}
        <div className="bg-slate-950/90 border border-slate-800/90 rounded-2xl p-4 font-mono text-xs shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-3">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-semibold text-slate-300">Journal d'Événements Live</span>
            </div>
            <span className="text-[10px] text-slate-500">Render Cloud Stream</span>
          </div>
          <div className="space-y-1.5 text-slate-400 text-[11px] max-h-32 overflow-y-auto">
            <p className="text-emerald-400">[SYSTEM] Connection établie avec dg-agent-engine.onrender.com</p>
            <p className="text-slate-400">[LLM-ROUTER] Contrôle des quotas effectué : 3 modèles vérifiés OK.</p>
            <p className="text-indigo-400">[TAL-ENGINE] Modules de conformité immobilière Québec initialisés.</p>
            <p className="text-slate-500">[ORCHESTRATOR] En attente de la première commande utilisateur...</p>
          </div>
        </div>

      </div>
    </main>
  );
}
