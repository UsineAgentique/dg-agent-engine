# Rapport de Situation Officiel - Usine Agentique

## 1. Architecture Globale
- **Backend**: FastAPI
- **Orchestration**: LangGraph
- **Base de données**: Supabase
- **Hébergement**: Render
- **Intégrations**: Slack API, GitHub API

## 2. Configuration de l'Orchestrateur Principal AMAL-DG
- **Modèle Principal**: DeepSeek-V3
- **Modèle Secondaire**: Llama 3.1 405B
- **Token Limit**: 8192

## 3. Cartographie des Pôles Modulaires

| Pôle | Dossier | Modèle Principal | Modèle Fallback | Sous-Agents |
|------|---------|------------------|-----------------|-------------|
| FIN | poles/fin | GPT-4 | Claude-2 | 8 agents spécialisés |
| TECH | poles/tech | GPT-4-Turbo | LLaMA-2 | 8 agents spécialisés |
| GOV | poles/gov | Claude-3 | GPT-4 | 8 agents spécialisés |
| GRO | poles/gro | GPT-4o | Mistral-Large | 8 agents spécialisés |
| SAL | poles/sal | Claude-3-Sonnet | GPT-3.5 | 8 agents spécialisés |
| SRC | poles/src | Gemini-1.5 | Claude-3-Opus | 8 agents spécialisés |
| RAD | poles/rad | GPT-4-Turbo | Claude-3 | 8 agents spécialisés |
| RET | poles/ret | Claude-3-Haiku | GPT-4 | 8 agents spécialisés |
| MED | poles/med | GPT-4-Med | Claude-3 | 8 agents spécialisés |