POLE_CONFIG = {
    'id': 'SAL',
    'name': 'VENTES, CLOSING & PROSPECTION B2B',
    'main_model': 'minimax/minimax-m3.1-flash',
    'fallback_model': 'gemini-3.8-flash',
    'subagents': [
        {
            'id': 'SAL-01',
            'name': 'Inbound Qualification Agent',
            'description': 'Qualification automatique des leads entrants, calcul du score BANT/MEDDIC.',
            'doctrine': 'Qualification instantanée et priorisation des leads à forte valeur.'
        },
        {
            'id': 'SAL-02',
            'name': 'Outbound SDR Agent',
            'description': 'Prospection active B2B, prise de contact ciblée et séquences de relance multi-canaux.',
            'doctrine': 'Génération continue de rendez-vous qualifiés.'
        },
        {
            'id': 'SAL-03',
            'name': 'Sales Proposal Architect',
            'description': 'Génération automatisée d'offres commerciales sur-mesure et propositions de valeur.',
            'doctrine': 'Offres percutantes alignées sur les besoins du client.'
        },
        {
            'id': 'SAL-04',
            'name': 'Objection Handling Specialist',
            'description': 'Traitement des objections tarifaires, techniques ou juridiques en temps réel.',
            'doctrine': 'Transformer chaque objection en opportunité de closing.'
        },
        {
            'id': 'SAL-05',
            'name': 'Account Executive & Closing Agent',
            'description': 'Négociation finale, closing contractuel et accélération du cycle de vente.',
            'doctrine': 'Maximiser le win-rate et raccourcir les cycles.'
        },
        {
            'id': 'SAL-06',
            'name': 'CRM & Pipeline Sync Agent',
            'description': 'Maintien et mise à jour en temps réel des données CRM, opportunités et stadiers de vente.',
            'doctrine': 'Visibilité et hygiène CRM irréprochables.'
        },
        {
            'id': 'SAL-07',
            'name': 'Account-Based Marketing Specialist',
            'description': 'Stratégie ABM ciblée sur les comptes grands comptes / entreprises cibles.',
            'doctrine': 'Infiltration et conversion stratégique des grands comptes.'
        },
        {
            'id': 'SAL-08',
            'name': 'Customer Expansion & Upsell Agent',
            'description': 'Détection des opportunités d'upsell, cross-sell et expansion du chiffre d'affaires.',
            'doctrine': 'Maximiser la valeur de vie client (LTV).'
        }
    ]
}