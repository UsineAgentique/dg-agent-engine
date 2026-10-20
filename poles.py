POLES_CONFIG = {
    "FIN": {
        "name": "BI, FINANCE & FISCALITÉ INTERNATIONALE",
        "main_model": "liquid/lfm2.5-2.6b",
        "fallback_model": "openai/gpt-oss-20b",
        "subagents": {
            "FIN-01": {
                "name": "CFO Systemic Agent",
                "description": "Direction financière, gestion de la trésorerie globale et rentabilité FCF.",
                "doctrine": "Rien ne prévaut sur le Free Cash Flow positif."
            },
            "FIN-02": {
                "name": "InternationalTaxVATAgent",
                "description": "Calcul automatisé TVA/GST/HST, Stripe Tax mondial et conformité transfrontalière.",
                "doctrine": "Zéro risque fiscal, conformité transfrontalière absolue."
            },
            "FIN-03": {
                "name": "FinOps Cost Minimizer",
                "description": "Arbitrage dynamique du coût des tokens, API et infrastructure compute.",
                "doctrine": "Chaque centime de compute doit rapporter $10."
            },
            "FIN-04": {
                "name": "Revenue Recognition Agent",
                "description": "Comptabilisation des abonnements SaaS (ARR/MRR) selon normes IFRS/US-GAAP.",
                "doctrine": "Rigueur comptable selon les normes IFRS/US-GAAP."
            },
            "FIN-05": {
                "name": "Predictive CashFlow Agent",
                "description": "Modélisation financière prédictive et projection de trésorerie à 12/36 mois.",
                "doctrine": "Anticiper les besoins en liquidités avant la crise."
            },
            "FIN-06": {
                "name": "Banking & Stripe Sync",
                "description": "Réconciliation automatique et synchronisation bancaire/passerelles en temps réel.",
                "doctrine": "Équilibre exact des comptes à la seconde près."
            },
            "FIN-07": {
                "name": "Audit & Fraud Detector",
                "description": "Détection des anomalies, audits financiers et prévention des tentatives de fraude.",
                "doctrine": "Vigilance paranoïaque sur chaque transaction."
            },
            "FIN-08": {
                "name": "Valuation & Cap Table Agent",
                "description": "Suivi dynamique de la dilution, valorisation et gestion de la Cap Table.",
                "doctrine": "Maximiser la valeur actionnariale à long terme."
            }
        }
    }
}