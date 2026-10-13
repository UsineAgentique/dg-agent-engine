'use client';

import { useState, useEffect } from 'react';

export default function Dashboard() {
  const [status, setStatus] = useState('Connecté Live ⚡');
  const [lastUpdate, setLastUpdate] = useState('');

  useEffect(() => {
    setLastUpdate(new Date().toLocaleTimeString());
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 font-sans">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800 pb-6 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              Amal-DG — Control Center
            </h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Supervision autonome des 8 pôles d'experts & Pilotage LLM en temps réel (TAL & Immobilier Québec)
          </p>
        </div>
        <div className="flex items-center gap-3 bg-slate-900/80 border border-slate-800 px-4 py-2 rounded-xl text-xs shadow-lg">
          <span className="text-slate-400">Moteur Render :</span>
          <span className="text-emerald-400 font-semibold">{status}</span>
          <span className="text-slate-500 text-[10px]">({lastUpdate})</span>
        </div>
      </header>

      {/* Main Grid */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Circuit Breaker / Models */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900/50 backdrop-blur border border-slate-800/80 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-blue-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
              État des Modèles & Quotas
            </h2>
            <div className="space-y-3">
              <div className="bg-slate-950/60 border border-slate-800 p-3.5 rounded-xl hover:border-slate-700 transition">
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-slate-200">google/gemma-4-31b-it</span>
                  <span className="text-emerald-400 text-[10px] px-2 py-0.5 bg-emerald-950/50 border border-emerald-800/50 rounded-full font-semibold">HEALTHY</span>
                </div>
                <div className="text-xs text-slate-400">Échecs : 0 | Quotas : OK (Free Tier)</div>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 p-3.5 rounded-xl hover:border-slate-700 transition">
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-slate-200">z-ai/glm-5.2</span>
                  <span className="text-emerald-400 text-[10px] px-2 py-0.5 bg-emerald-950/50 border border-emerald-800/50 rounded-full font-semibold">HEALTHY</span>
                </div>
                <div className="text-xs text-slate-400">Échecs : 0 | Quotas : OK (Free Tier)</div>
              </div>
              <div className="bg-slate-950/60 border border-slate-800 p-3.5 rounded-xl hover:border-slate-700 transition">
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-slate-200">google/gemma-4-26b</span>
                  <span className="text-emerald-400 text-[10px] px-2 py-0.5 bg-emerald-950/50 border border-emerald-800/50 rounded-full font-semibold">HEALTHY</span>
                </div>
                <div className="text-xs text-slate-400">Échecs : 0 | Quotas : OK (Free Tier)</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right 2 Columns: 8 Poles Status */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900/50 backdrop-blur border border-slate-800/80 rounded-2xl p-6 shadow-xl">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-indigo-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
              Répartition & Statut des 8 Pôles d'Experts
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-blue-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">01. Produit & Vision</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Analytique SaaS</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-indigo-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">02. Juridique (TAL & Loi 25)</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Droit Immobilier QC</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-purple-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">03. Architecture SaaS</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Fullstack & Cloud</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-pink-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-pink-400 uppercase tracking-wider">04. UX/UI & Expérience</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Design System B2B</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-emerald-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">05. Growth & Marché QC</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Acquisition PropTech</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-amber-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">06. Finance & Modèle Éco</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Tarification SaaS</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-cyan-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">07. Sécurité & Conformité</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Loi 25 & Privacy</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

              <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl hover:border-rose-500/50 transition group">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">08. Pilotage & Orchestration</span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">IDLE</span>
                </div>
                <div className="text-sm font-medium text-slate-100 mb-1">Profil : Master Agent DG</div>
                <div className="text-xs text-slate-400">En attente de mission tactique</div>
              </div>

            </div>
          </div>
        </div>

      </div>
    </main>
  );
}
