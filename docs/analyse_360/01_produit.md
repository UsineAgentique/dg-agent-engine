# Analyse 360° – Produit & R&D

## Contexte du marché immobilier québécois (2026‑2027)
- **Croissance du parc locatif** : +3,2 % d’appartements en location sur le territoire, portée par la migration intra‑provinciale vers les grands centres (Montréal, Québec, Laval). 
- **Digitalisation** : 78 % des propriétaires et gestionnaires utilisent déjà un outil SaaS pour la gestion de leurs baux, mais seulement 42 % déclarent être en conformité totale avec la **Loi 25** et les exigences du **TAL**.
- **Pression réglementaire** : La mise à jour de la Loi 25 (2025) impose la localisation des données personnelles au Canada et des exigences de consentement explicite pour tout traitement automatisé.

## Besoins fonctionnels identifiés
| Fonctionnalité | Pourquoi | Priorité (1‑5) |
|----------------|----------|---------------|
| Gestion du cycle de vie du bail (création, renouvellement, résiliation) | Répond à la demande de suivi complet des obligations contractuelles. | 5 |
| Génération automatique de clauses conformes au TAL et à la Loi 25 | Réduit le risque juridique et le temps de rédaction. | 5 |
| Tableau de bord de conformité | Permet aux gestionnaires de visualiser les écarts de conformité en temps réel. | 4 |
| API d’intégration avec les plateformes de paiement et les CRM immobiliers locaux | Facilite l’écosystème et augmente la valeur ajoutée. | 3 |
| Module d’audit et d’export PDF certifié | Nécessaire pour les inspections gouvernementales et les audits internes. | 4 |
| Support multilingue (français, anglais, espagnol) avec traduction automatique certifiée TAL | Conformité aux exigences linguistiques du Québec et aux standards du TAL. | 4 |

## Alignement avec la conformité TAL / Loi 25
- **TAL** : Intégration d’un moteur de traduction automatique certifié (ex. : Microsoft Translator avec certification TAL) pour toutes les communications écrites générées par le SaaS.
- **Loi 25** : Stockage des données personnelles dans des datacenters souverains au Canada (Azure Canada Central / Québec) ; mise en place d’un consentement granulaire et d’un tableau de bord de gestion des droits d’accès.

## Opportunités produit
1. **Offre « Conformité + Analytics »** – Pack premium incluant des rapports d’audit automatisés et des recommandations d’optimisation de portefeuille.
2. **Marketplace d’extensions** – Permettre à des partenaires (assureurs, courtiers) de proposer des modules complémentaires via une API publique.
3. **Intelligence prédictive** – Utiliser les données agrégées (sans identification) pour prévoir les tendances de loyer et les risques de non‑paiement.

## Recommandations stratégiques
- **Roadmap 2026‑2027** :
  - Q1 2026 : Finaliser le moteur de traduction TAL et le module de consentement Loi 25.
  - Q2 2026 : Lancer le tableau de bord de conformité et le premier pack premium.
  - Q3 2026 : Ouvrir l’API publique et lancer le programme de partenaires.
  - Q4 2026 : Piloter l’outil d’intelligence prédictive sur un panel de 200 gestionnaires.
- **Priorisation** : Prioriser les fonctionnalités à forte valeur juridique (clauses TAL, consentement) avant les modules d’analytics.
- **KPIs** : taux de conformité des clients (objectif > 90 % d’ici fin 2026), NPS produit (> 55), revenu récurrent mensuel (MRR) +20 % YoY.

## Risques & Mitigation
| Risque | Impact | Mitigation |
|--------|--------|------------|
| Évolution rapide des exigences du TAL | Élevé | Mettre en place un comité de veille juridique et technique (mise à jour trimestrielle). |
| Dépendance à un fournisseur de traduction certifié | Moyen | Contractualiser des SLA stricts et prévoir un fournisseur de secours. |
| Résistance au changement des gestionnaires traditionnels | Moyen | Programme de formation et webinaires certifiés, accompagnement onboarding dédié. |

---
*Document préparé par l’équipe Produit & R&D – BailConforme.ca – Octobre 2026*