# Rapport de Situation Officiel – Usine Agentique

## 1. Architecture Globale
- **FastAPI** : Framework principal pour les API
- **LangGraph** : Orchestration des workflows agentiques
- **Supabase** : Base de données et authentification
- **Render** : Hébergement et déploiement
- **Slack API** : Communication et notifications
- **GitHub API** : Gestion des dépôts et CI/CD

## 2. Configuration de l'Orchestrateur Principal AMAL-DG
- **Modèle Principal** : DeepSeek-V3
- **Modèle Secondaire** : Llama 3.1 405B
- **Token Limit** : 8192

## 3. Cartographie des 9 Pôles Modulaires
| Pôle | Dossier | Modèle Principal | Modèle Secondaire | Sous-Agents |
|------|---------|------------------|-------------------|-------------|
| **FIN** | `poles/FIN/config.py` | Llama 3.1 405B | DeepSeek-V3 | 8 sous-agents spécialisés |
| **TECH** | `poles/TECH/config.py` | DeepSeek-V3 | Llama 3.1 405B | 8 sous-agents spécialisés |
| **GOV** | `poles/GOV/config.py` | Llama 3.1 405B | DeepSeek-V3 | 8 sous-agents spécialisés |
| **GRO** | `poles/GRO/config.py` | DeepSeek-V3 | Llama 3.1 405B | 8 sous-agents spécialisés |
| **SAL** | `poles/SAL/config.py` | Llama 3.1 405B | DeepSeek-V3 | 8 sous-agents spécialisés |
| **SRC** | `poles/SRC/config.py` | DeepSeek-V3 | Llama 3.1 405B | 8 sous-agents spécialisés |
| **RAD** | `poles/RAD/config.py` | Llama 3.1 405B | DeepSeek-V3 | 8 sous-agents spécialisés |
| **RET** | `poles/RET/config.py` | DeepSeek-V3 | Llama 3.1 405B | 8 sous-agents spécialisés |
| **MED** | `poles/MED/config.py` | Llama 3.1 405B | DeepSeek-V3 | 8 sous-agents spécialisés |