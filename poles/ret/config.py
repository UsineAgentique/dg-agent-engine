POLE_CONFIG = {
    'Identifiant': 'RET',
    'Nom Complet': 'RÉTENTION, CUSTOMER SUCCESS & PRISE DE DÉCISION',
    'Modèle Principal': 'inception/mercury-decide (OpenRouter)',
    'Modèle Fallback': 'llama-3.3-70b-versatile (Groq)',
    'Sous-agents': [
        {
            'Nom': 'Churn Prediction & Early Warning',
            'Identifiant': 'RET-01',
            'Description': 'Détection précoce des risques de résiliation via l'analyse comportementale et l'usage produit.',
            'Doctrine': 'Identifier et traiter le churn avant qu'il ne se produise.'
        },
        {
            'Nom': 'Customer Success & Onboarding Specialist',
            'Identifiant': 'RET-02',
            'Description': 'Optimisation du parcours d'intégration (onboarding), activation produit et accompagnement client.',
            'Doctrine': 'Maximiser la valeur perçue dès les 14 premiers jours.'
        },
        {
            'Nom': 'Support & Automated Helpdesk Agent',
            'Identifiant': 'RET-03',
            'Description': 'Resolution automatisée des tickets de support, FAQ intelligente et assistance technique 24/7.',
            'Doctrine': 'Résolution au premier contact et satisfaction maximale.'
        },
        {
            'Nom': 'Net Promoter Score & Feedback Miner',
            'Identifiant': 'RET-04',
            'Description': 'Collecte et analyse des avis clients, enquêtes NPS et retours d'expérience produit.',
            'Doctrine': 'Voix du client intégrée dans la boucle de décision.'
        },
        {
            'Nom': 'Account Health Monitor',
            'Identifiant': 'RET-05',
            'Description': 'Scoring en temps réel de la santé des comptes utilisateurs et déclenchement d'alertes proactives.',
            'Doctrine': 'Maintien d'un score de santé client toujours au vert.'
        },
        {
            'Nom': 'Decision Support & Strategic Arbitrator',
            'Identifiant': 'RET-06',
            'Description': 'Moteur d'arbitrage stratégique, analyse d'impact et aide à la décision pour la Direction.',
            'Doctrine': 'Décisions éclairées par la donnée et la logique d'impact.'
        },
        {
            'Nom': 'Renewal & Contract Retention Agent',
            'Identifiant': 'RET-07',
            'Description': 'Gestion des renouvellements de contrats SaaS, négociation de rétention et offres anti-churn.',
            'Doctrine': 'Conserver chaque compte à haute valeur ajoutée.'
        },
        {
            'Nom': 'Advocacy & Testimonial Manager',
            'Identifiant': 'RET-08',
            'Description': 'Transformation des clients satisfaits en ambassadeurs, étude de cas et collecte de témoignages.',
            'Doctrine': 'Faire de la satisfaction client un moteur de preuve sociale.'
        }
    ]
}