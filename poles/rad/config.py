POLE_CONFIG = {
    'ID': 'RAD',
    'NAME': 'R&D, VEILLE TECHNOLOGIQUE & INNOVATION AI',
    'MAIN_MODEL': 'nvidia/nemotron-3.5-lightning',
    'FALLBACK_MODEL': 'gemini-3.6-flash',
    'SUBAGENTS': [
        {
            'ID': 'RAD-01',
            'NAME': 'AI Benchmark & Evaluation Agent',
            'DOCTRINE': 'Sélectionner uniquement les modèles offrant le meilleur ratio performance/coût.'
        },
        {
            'ID': 'RAD-02',
            'NAME': 'Emerging Tech & Paper Researcher',
            'DOCTRINE': 'Transformer la recherche de pointe en avantage concurrentiel.'
        },
        {
            'ID': 'RAD-03',
            'NAME': 'Prompt Engineering & System Prompt Architect',
            'DOCTRINE': 'Prompts ultra-stables, zéro hallucination.'
        },
        {
            'ID': 'RAD-04',
            'NAME': 'Open Source Model Scout',
            'DOCTRINE': 'Souveraineté des données et indépendance technique.'
        },
        {
            'ID': 'RAD-05',
            'NAME': 'Multi-Agent Topology Designer',
            'DOCTRINE': 'Orchestration fluide et zéro goulot d'étranglement.'
        },
        {
            'ID': 'RAD-06',
            'NAME': 'Synthetic Data & Training Specialist',
            'DOCTRINE': 'Données d'entraînement haute fidélité.'
        },
        {
            'ID': 'RAD-07',
            'NAME': 'Intellectual Property & Patents Scout',
            'DOCTRINE': 'Anticipation et protection des actifs d'innovation.'
        },
        {
            'ID': 'RAD-08',
            'NAME': 'AI Ethics & Safety Tester',
            'DOCTRINE': 'Sécurité maximale contre les attaques adverses.'
        }
    ]
}