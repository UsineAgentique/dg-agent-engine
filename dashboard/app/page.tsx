'use client';

import { useState, useEffect } from 'react';

// Structure des sous-agents par pôle
interface SubAgent {
  id: string;
  name: string;
  role: string;
  status: 'RUNNING' | 'IDLE' | 'COMPLETED' | 'ERROR';
  llm: string;
  currentTask: string;
  progress: number;
}

interface Pole {
  id: string;
  name: string;
  role: string;
  color: string;
  border: string;
  bgGlow: string;
  description: string;
  subAgents: SubAgent[];
}

export default function Dashboard() {
  const [status, setStatus] = useState('Opérationnel ⚡');
  const [lastUpdate, setLastUpdate] = useState('');
  const [selectedPole, setSelectedPole] = useState<Pole | null>(null);

  useEffect(() => {
    setLastUpdate(new Date().toLocaleTimeString());
    const interval = setInterval(() => {
      setLastUpdate(new Date().toLocaleTimeString());
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Définition des 8 pôles avec leurs sous-agents en cours d'exécution
  const poles: Pole[] = [
    {
      id: '01',
      name: 'Produit & Stratégie',
      role: 'Analyse & Roadmap Swarm',
      color: 'text-blue-400',
      border: 'hover:border-blue-500/50',
      bgGlow: 'from-blue-500/10',
      description: 'Définition des spécifications, découpage des fonctionnalités et alignement stratégique.',
      subAgents: [
        { id: 'SA-011', name: 'Agent Product Spec', role: 'Rédaction User Stories', status: 'RUNNING', llm: 'google/gemma-4-26b', currentTask: 'Génération du backlog fonctionnel MVP', progress: 75 },
        { id: 'SA-012', name: 'Agent Competitive Analysis', role: 'Benchmark SaaS', status: 'COMPLETED', llm: 'meta-llama/llama-3-8b', currentTask: 'Analyse comparative des features', progress: 100 },
        { id: 'SA-013', name: 'Agent Roadmap Planner', role: 'Planification Jalons', status: 'IDLE', llm: 'google/gemma-4-26b', currentTask: 'En attente de validation backlog', progress: 0 }
      ]
    },
    {
      id: '02',
      name: 'Architecture System',
      role: 'Design & Topologie Cloud',
      color: 'text-indigo-400',
      border: 'hover:border-indigo-500/50',
      bgGlow: 'from-indigo-500/10',
      description: 'Modélisation du Swarm, schéma de base de données et contrats d’API.',
      subAgents: [
        { id: 'SA-021', name: 'Agent Swarm Architect', role: 'Topologie Microservices', status: 'RUNNING', llm: 'google/gemma-4-31b-it', currentTask: 'Optimisation du graphe DAG d orchestration', progress: 60 },
        { id: 'SA-022', name: 'Agent Database Modeler', role: 'Schema PostgreSQL/Redis', status: 'IDLE', llm: 'google/gemma-4-26b', currentTask: 'En attente des specs Produit', progress: 0 }
      ]
    },
    {
      id: '03',
      name: 'Backend & API Engine',
      role: 'FastAPI & Services Render',
      color: 'text-purple-400',
      border: 'hover:border-purple-500/50',
      bgGlow: 'from-purple-500/10',
      description: 'Développement des endpoints REST/WebSocket, connecteurs LLM et fil d exécution.',
      subAgents: [
        { id: 'SA-031', name: 'Agent FastAPI Dev', role: 'Routes & Controllers', status: 'RUNNING', llm: 'google/gemma-4-26b', currentTask: 'Implémentation des endpoints Webhook Swarm', progress: 85 },
        { id: 'SA-032', name: 'Agent LLM Router', role: 'Circuit Breaker & Failover', status: 'RUNNING', llm: 'z-ai/glm-5.2', currentTask: 'Monitoring de latence des 4 modèles', progress: 90 },
        { id: 'SA-033', name: 'Agent Worker Dispatcher', role: 'Queue Manager', status: 'IDLE', llm: 'meta-llama/llama-3-8b', currentTask: 'Prêt pour allocation de tâches', progress: 0 }
      ]
    },
    {
      id: '04',
      name: 'Frontend & UI Control',
      role: 'Next.js & Tailwind Vercel',
      color: 'text-pink-400',
      border: 'hover:border-pink-500/50',
      bgGlow: 'from-pink-500/10',
      description: 'Interface de contrôle temps réel, composants interactifs et visuels B2B.',
      subAgents: [
        { id: 'SA-041', name: 'Agent UI Designer', role: 'Design System & Modals', status: 'RUNNING', llm: 'google/gemma-4-26b', currentTask: 'Intégration des modals de détails par pôle', progress: 95 },
        { id: 'SA-042', name: 'Agent Telemetry Stream', role: 'Sockets & Live Sync', status: 'COMPLETED', llm: 'meta-llama/llama-3-8b', currentTask: 'Connexion du flux de logs temps réel', progress: 100 }
      ]
    },
    {
      id: '05',
      name: 'Sécurité & Privacy',
      role: 'Contrôle & Isolation Sandbox',
      color: 'text-emerald-400',
      border: 'hover:border-emerald-500/50',
      bgGlow: 'from-emerald-500/10',
      description: 'Sécurisation des clés API, isolation du code exécuté et audits de vulnérabilités.',
      subAgents: [
        { id: 'SA-051', name: 'Agent Secrets Guard', role: 'Vault & Env Checker', status: 'RUNNING', llm: 'google/gemma-4-31b-it', currentTask: 'Audit de chiffrement des variables Vercel/Render', progress: 40 },
        { id: 'SA-052', name: 'Agent Sandbox Inspector', role: 'Contrôle Execution Code', status: 'IDLE', llm: 'meta-llama/llama-3-8b', currentTask: 'Surveillance des appels système', progress: 0 }
      ]
    },
    {
      id: '06',
      name: 'QA & Tests Automatisés',
      role: 'Validation & Robustesse',
      color: 'text-amber-400',
      border: 'hover:border-amber-500/50',
      bgGlow: 'from-amber-500/10',
      description: 'Tests unitaires, tests de charge et vérification de la résilience du Swarm.',
      subAgents: [
        { id: 'SA-061', name: 'Agent Unit Test Runner', role: 'Pytest Suite', status: 'COMPLETED', llm: 'meta-llama/llama-3-8b', currentTask: 'Validation de la suite de tests unitaires', progress: 100 },
        { id: 'SA-062', name: 'Agent Load Tester', role: 'Simulations Concurrence', status: 'IDLE', llm: 'google/gemma-4-26b', currentTask: 'En attente du build de recette', progress: 0 }
      ]
    },
    {
      id: '07',
      name: 'DevOps & Pipeline CI/CD',
      role: 'GitHub & Déploiement Cloud',
      color: 'text-cyan-400',
      border: 'hover:border-cyan-500/50',
      bgGlow: 'from-cyan-500/10',
      description: 'Automatisation des builds, intégration continue GitHub Actions et synchro Vercel.',
      subAgents: [
        { id: 'SA-071', name: 'Agent Vercel Sync', role: 'Deployment Automation', status: 'RUNNING', llm: 'google/gemma-4-26b', currentTask: 'Build & Deploy automatique sur Vercel', progress: 100 },
        { id: 'SA-072', name: 'Agent Render Monitor', role: 'Healthcheck Backend', status: 'RUNNING', llm: 'meta-llama/llama-3-8b', currentTask: 'Ping toutes les 5s sur Render Live Engine', progress: 100 }
      ]
    },
    {
      id: '08',
      name: 'Master Orchestrator (DG)',
      role: 'Pilotage Central & Dispatch',
      color: 'text-rose-400',
      border: 'hover:border-rose-500/50',
      bgGlow: 'from-rose-500/10',
      description: 'Agent Maître Amal-DG : coordination générale, arbitrage LLM et supervision.',
      subAgents: [
        { id: 'SA-081', name: 'Amal-DG Core Engine', role: 'Master Brain', status: 'RUNNING', llm: 'google/gemma-4-31b-it', currentTask: 'Analyse et arbitrage des requêtes du Swarm', progress: 100 },
        { id: 'SA-082', name: 'Amal-DG Strategy Backup', role: 'Fallback Brain', status: 'IDLE', llm: 'z-ai/glm-5.2', currentTask: 'Hot Standby (Failover automatique)', progress: 0 }
      ]
    }
  ];

  return (
    <main className="min-h-screen bg-[#030712] text-slate-100 p-4 sm:p-6 md:p-10 font-sans selection:bg-cyan-500 selection:text-black">
      
      {/* Dynamic Background */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))] pointer-events-none"></div>

      {/* Header */}
      <header className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row justify-between items-start md:items-center border-b border-slate-800/80 pb-6 gap-4 relative z-10">
        <div>
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-500 bg-clip-text text-transparent">
              Amal-DG — Swarm Control Center
            </h1>
            <span className="text-[10px] bg-cyan-950/80 border border-cyan-800/60 text-cyan-400 px-2.5 py-0.5 rounded-full font-mono font-semibold uppercase tracking-wider">
              v1.0 Live
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Supervision du Swarm Agentique — Cliquez sur un pôle pour afficher les sous-agents en cours d execution
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
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Pôles du Swarm</div>
            <div className="text-2xl font-bold text-white font-mono">8 Pôles</div>
            <div className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
              <span>●</span> 17 Sous-agents prêts
            </div>
          </div>
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Architecture LLM</div>
            <div className="text-2xl font-bold text-cyan-400 font-mono">4 Modèles</div>
            <div className="text-[10px] text-slate-400 mt-1">2 Master + 2 Workers</div>
          </div>
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Sous-Agents Actifs</div>
            <div className="text-2xl font-bold text-indigo-400 font-mono">9 En cours</div>
            <div className="text-[10px] text-indigo-300 mt-1">Exécution parallèle</div>
          </div>
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Latence Engine</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">128 ms</div>
            <div className="text-[10px] text-emerald-400 mt-1">Render Cloud Stream</div>
          </div>
        </div>

        {/* Grid des 8 Pôles */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <span className="text-indigo-400">📊</span> Les 8 Pôles d Experts (Fenêtres Interactives)
            </h2>
            <span className="text-xs text-slate-400">Cliquez sur une carte pour inspecter le pôle</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {poles.map((pole) => {
              const activeCount = pole.subAgents.filter(a => a.status === 'RUNNING').length;
              return (
                <div 
                  key={pole.id}
                  onClick={() => setSelectedPole(pole)}
                  className={`bg-slate-900/60 backdrop-blur border border-slate-800/90 rounded-2xl p-5 cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl ${pole.border} group relative overflow-hidden`}
                >
                  <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${pole.bgGlow} to-transparent`}></div>
                  
                  <div className="flex justify-between items-start mb-3">
                    <span className={`text-xs font-bold uppercase tracking-wider ${pole.color}`}>
                      {pole.id}. {pole.name}
                    </span>
                    {activeCount > 0 ? (
                      <span className="text-[9px] bg-emerald-950/80 border border-emerald-800/80 text-emerald-400 px-2 py-0.5 rounded-full font-mono flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        {activeCount} ACTIF{activeCount > 1 ? 'S' : ''}
                      </span>
                    ) : (
                      <span className="text-[9px] bg-slate-800/80 border border-slate-700/80 text-slate-400 px-2 py-0.5 rounded font-mono">
                        STANDBY
                      </span>
                    )}
                  </div>

                  <div className="text-xs font-semibold text-slate-200 mb-1">{pole.role}</div>
                  <div className="text-[11px] text-slate-400 line-clamp-2 mb-4">{pole.description}</div>

                  <div className="flex justify-between items-center text-[10px] text-slate-500 pt-3 border-t border-slate-800/60">
                    <span>{pole.subAgents.length} sous-agents</span>
                    <span className={`${pole.color} group-hover:underline font-semibold flex items-center gap-1`}>
                      Ouvrir la fenêtre &rarr;
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Live Terminal */}
        <div className="bg-slate-950/90 border border-slate-800/90 rounded-2xl p-4 font-mono text-xs shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-3">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-semibold text-slate-300">Journal d Exécution du Swarm (Live Stream)</span>
            </div>
            <span className="text-[10px] text-slate-500">Render Engine Log</span>
          </div>
          <div className="space-y-1.5 text-slate-400 text-[11px] max-h-32 overflow-y-auto">
            <p className="text-emerald-400">[SYSTEM] Swarm Control Center synchronisé avec Render.</p>
            <p className="text-cyan-400">[EXECUTION] Pôle 07 (DevOps) : SA-071 build & deploy Vercel terminé à 100%.</p>
            <p className="text-blue-400">[EXECUTION] Pôle 01 (Produit) : SA-011 génère le backlog (75%).</p>
            <p className="text-purple-400">[EXECUTION] Pôle 03 (Backend) : SA-031 déploie les routes FastAPI (85%).</p>
          </div>
        </div>

      </div>

      {/* MODAL / FENÊTRE DE DÉTAIL DU PÔLE SÉLECTIONNÉ */}
      {selectedPole && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-2xl relative animate-in fade-in zoom-in duration-200">
            
            {/* Modal Header */}
            <div className="flex justify-between items-start border-b border-slate-800 pb-4 mb-6">
              <div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-extrabold uppercase tracking-wider ${selectedPole.color}`}>
                    Pôle {selectedPole.id}
                  </span>
                  <span className="text-[10px] bg-slate-800 border border-slate-700 text-slate-300 px-2 py-0.5 rounded font-mono">
                    {selectedPole.subAgents.length} Sous-Agents
                  </span>
                </div>
                <h3 className="text-2xl font-bold text-white mt-1">{selectedPole.name}</h3>
                <p className="text-xs text-slate-400 mt-1">{selectedPole.description}</p>
              </div>

              <button 
                onClick={() => setSelectedPole(null)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-full p-2 text-xs transition"
              >
                ✕ Fermer
              </button>
            </div>

            {/* Sub-Agents Execution List */}
            <div className="space-y-4">
              <h4 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                ⚡ Sous-agents & Tâches en cours d execution
              </h4>

              <div className="space-y-3">
                {selectedPole.subAgents.map((agent) => (
                  <div key={agent.id} className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-3">
                    
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold font-mono text-cyan-400">{agent.id}</span>
                          <span className="text-sm font-semibold text-slate-100">{agent.name}</span>
                        </div>
                        <span className="text-xs text-slate-400">{agent.role}</span>
                      </div>

                      {/* Status Badge */}
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-800 px-2 py-1 rounded">
                          LLM: {agent.llm}
                        </span>
                        {agent.status === 'RUNNING' && (
                          <span className="text-[10px] bg-emerald-950 border border-emerald-800 text-emerald-400 px-2.5 py-1 rounded-full font-bold font-mono flex items-center gap-1.5">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                            RUNNING
                          </span>
                        )}
                        {agent.status === 'COMPLETED' && (
                          <span className="text-[10px] bg-blue-950 border border-blue-800 text-blue-400 px-2.5 py-1 rounded-full font-bold font-mono">
                            ✓ COMPLETED
                          </span>
                        )}
                        {agent.status === 'IDLE' && (
                          <span className="text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-2.5 py-1 rounded-full font-bold font-mono">
                            IDLE
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Task Progress Bar */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-300 font-mono">Tâche : {agent.currentTask}</span>
                        <span className="text-slate-400 font-mono">{agent.progress}%</span>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                        <div 
                          className={`h-full transition-all duration-500 ${
                            agent.status === 'COMPLETED' ? 'bg-blue-500' :
                            agent.status === 'RUNNING' ? 'bg-emerald-500' : 'bg-slate-700'
                          }`}
                          style={{ width: `${agent.progress}%` }}
                        ></div>
                      </div>
                    </div>

                  </div>
                ))}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="mt-6 pt-4 border-t border-slate-800 flex justify-end">
              <button 
                onClick={() => setSelectedPole(null)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition shadow-lg"
              >
                Retour au Swarm Control
              </button>
            </div>

          </div>
        </div>
      )}

    </main>
  );
}
