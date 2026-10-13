'use client';
import { useState, useEffect } from 'react';

const POLES_CONFIG = [
  { key: 'team3_product', label: '01. Pôle Produit & Vision', profile: 'analytique', icon: '🚀' },
  { key: 'team_legal', label: '02. Pôle Juridique (TAL & Loi 25)', profile: 'juridique', icon: '⚖️' },
  { key: 'team5_growth_seo', label: '03. Pôle Growth & SEO', profile: 'analytique', icon: '📈' },
  { key: 'team_finance', label: '04. Pôle Finance & Modèle B2B', profile: 'juridique', icon: '💰' },
  { key: 'team_dev', label: '05. Pôle Architecture & Dev API', profile: 'technique', icon: '⚙️' },
  { key: 'team_secops', label: '06. Pôle SecOps & Sécurité', profile: 'technique', icon: '🔒' },
  { key: 'team_sales', label: '07. Pôle Ventes & ABM', profile: 'analytique', icon: '🤝' },
  { key: 'team_ux', label: '08. Pôle UX/UI & Parcours', profile: 'analytique', icon: '🎨' },
];

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = async () => {
    try {
      const res = await fetch('https://dg-agent-engine.onrender.com/api/dashboard-data');
      const json = await res.json();
      setData(json);
      setLoading(false);
    } catch (err) {
      console.error("Erreur de connexion au backend Render", err);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 3000);
    return () => clearInterval(interval);
  }, []);

  const getPoleStatus = (poleKey: string) => {
    if (!data || !data.execution_history) return { status: 'IDLE', details: 'En attente de mission', model: '-' };
    const log = data.execution_history.find((l: any) => l.pole.toLowerCase().includes(poleKey.toLowerCase()) || l.pole === poleKey);
    return log || { status: 'IDLE', details: 'En attente de mission', model: '-' };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center font-sans">
        <div className="text-center animate-pulse">
          <h2 className="text-xl font-bold">Connexion au réseau Amal-DG...</h2>
          <p className="text-slate-500 text-sm mt-2">Chargement de la télémétrie des sous-agents</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10 font-sans">
      <header className="border-b border-slate-800 pb-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <span>🤖</span> Amal-DG — Control Center
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Supervision autonome des 8 Pôles d'experts & Pilotage LLM en temps réel (BailConforme.ca)
          </p>
        </div>
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-lg">
          <span className="w-3 h-3 rounded-full bg-emerald-500 animate-ping"></span>
          <span className="text-xs font-semibold text-emerald-400">Moteur Render Live</span>
        </div>
      </header>

      <section className="mb-10">
        <h2 className="text-lg font-bold text-slate-200 mb-4">⚡ État des Modèles & Quotas (Circuit Breaker)</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(data.models_health || {}).map(([model, info]: [string, any]) => (
            <div key={model} className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
              <span className="text-xs font-mono text-slate-500 truncate block">{model}</span>
              <div className="flex justify-between items-center mt-3">
                <span className={`text-sm font-bold px-2.5 py-1 rounded-md ${
                  info.status === 'HEALTHY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-red-950 text-red-400 border border-red-800'
                }`}>
                  ● {info.status}
                </span>
                <span className="text-xs text-slate-400">Échecs: <strong className="text-white">{info.fails}</strong></span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-lg font-bold text-slate-200 mb-4">🏢 Répartition & Statut des 8 Pôles</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {POLES_CONFIG.map((pole) => {
            const current = getPoleStatus(pole.key);
            const isRunning = current.status === 'IN_PROGRESS';
            const isSuccess = current.status === 'SUCCESS';
            const isWarning = current.status === 'WARNING' || current.status === 'FALLBACK';

            return (
              <div key={pole.key} className={`bg-slate-900 border rounded-xl p-5 flex flex-col justify-between transition-all duration-300 ${
                isRunning ? 'border-amber-500 shadow-amber-500/10 shadow-lg' : 'border-slate-800'
              }`}>
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-2xl">{pole.icon}</span>
                    <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded ${
                      isRunning ? 'bg-amber-950 text-amber-400 animate-pulse' :
                      isSuccess ? 'bg-emerald-950 text-emerald-400' :
                      isWarning ? 'bg-yellow-950 text-yellow-400' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {current.status}
                    </span>
                  </div>
                  <h3 className="font-bold text-white text-sm mb-1">{pole.label}</h3>
                  <p className="text-xs font-mono text-slate-500 mb-3">Profil : {pole.profile}</p>
                </div>
                
                <div className="bg-slate-950 rounded-lg p-3 border border-slate-800/80 text-xs">
                  <div className="text-slate-400 truncate mb-1" title={current.details}>
                    {current.details}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 truncate">
                    Modèle: {current.model !== '-' ? current.model : 'En attente'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <h2 className="text-lg font-bold text-slate-200 mb-4">📋 Flux Brut des Opérations</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                <th className="pb-3 px-3">Horodatage (UTC)</th>
                <th className="pb-3 px-3">Pôle / Cible</th>
                <th className="pb-3 px-3">Modèle Utilisé</th>
                <th className="pb-3 px-3">Statut & Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-sm">
              {(!data.execution_history || data.execution_history.length === 0) ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-slate-500">Aucune action enregistrée pour le moment. Lance une mission sur Slack !</td>
                </tr>
              ) : (
                data.execution_history.map((log: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 font-mono text-xs text-slate-400">{log.timestamp}</td>
                    <td className="py-3 px-3 font-semibold text-white">{log.pole}</td>
                    <td className="py-3 px-3 font-mono text-xs text-slate-400">{log.model}</td>
                    <td className="py-3 px-3">
                      <span className={`inline-block font-medium text-xs px-2 py-0.5 rounded mr-2 ${
                        log.status === 'SUCCESS' ? 'bg-emerald-950 text-emerald-400' :
                        log.status === 'IN_PROGRESS' ? 'bg-amber-950 text-amber-400' :
                        log.status === 'FALLBACK' ? 'bg-purple-950 text-purple-400' : 'bg-red-950 text-red-400'
                      }`}>
                        {log.status}
                      </span>
                      <span className="text-slate-300 text-xs">{log.details}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
