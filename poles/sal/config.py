POLE_CONFIG = {
    'ID': 'SAL',
    'NAME': 'VENTES, CLOSING & PROSPECTION B2B',
    'MAIN_MODEL': 'minimax/minimax-m3.1-flash',
    'FALLBACK_MODEL': 'gemini-3.8-flash',
    'SUBAGENTS': [
        {
            'ID': 'SAL-01',
            'NAME': 'Inbound Qualification Agent',
            'DESCRIPTION': 'Qualification automatique des leads entrants, calcul du score BANT/MEDDIC.',
            'DOCTRINE': 'Qualification instantanée et priorisation des leads à forte valeur.'
        },
        {
            'ID': 'SAL-02',
            'NAME': 'Outbound SDR Agent',
            'DESCRIPTION': 'Prospection active B2B, prise de contact ciblée et séquences de relance multi-canaux.',
            'DOCTRINE': 'Génération continue de rendez-vous qualifiés.'
        },
        {
            'ID': 'SAL-03',
            'NAME': 'Sales Proposal Architect',
            'DESCRIPTION': 'Génération automatisée d'offres commerciales sur-mesure et propositions de valeur.',
            'DOCTRINE': 'Offres percutantes alignées sur les besoins du client.'
        },
        {
            'ID': 'SAL-04',
            'NAME': 'Objection Handling Specialist',
            'DESCRIPTION': 'Traitement des objections tarifaires, techniques ou juridiques en temps réel.',
            'DOCTRINE': 'Transformer chaque objection en opportunité de closing.'
        },
        {
            'ID': 'SAL-05',
            'NAME': 'Account Executive & Closing Agent',
            'DESCRIPTION': 'Négociation finale, closing contractuel et accélération du cycle de vente.',
            'DOCTRINE': 'Maximiser le win-rate et raccourcir les cycles.'
        },
        {
            'ID': 'SAL-06',
            'NAME': 'CRM & Pipeline Sync Agent',
            'DESCRIPTION': 'Maintien et mise à jour en temps réel des données CRM, opportunités et stadiers de vente.',
            'DOCTRINE': 'Visibilité et hygiène CRM irréprochables.'
        },
        {
            'ID': 'SAL-07',
            'NAME': 'Account-Based Marketing Specialist',
            'DESCRIPTION': 'Stratégie ABM ciblée sur les comptes grands comptes / entreprises cibles.',
            'DOCTRINE': 'Infiltration et conversion stratégique des grands comptes.'
        },
        {
            'ID': 'SAL-08',
            'NAME': 'Customer Expansion & Upsell Agent',
            'DESCRIPTION': 'Détection des opportunités d'upsell, cross-sell et expansion du chiffre d'affaires.',
            'DOCTRINE': 'Maximiser la valeur de vie client (LTV).'
        }
    ]
}