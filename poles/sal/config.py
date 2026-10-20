POLE_CONFIG = {
    'id': 'SAL',
    'name': 'VENTES, CLOSING & PROSPECTION B2B',
    'main_model': 'minimax/minimax-m3.1-flash',
    'fallback_model': 'gemini-3.8-flash',
    'subagents': [
        {'id': 'SAL-01', 'name': 'Inbound Qualification Agent', 'doctrine': 'Qualification instantanée et priorisation des leads à forte valeur.'},
        {'id': 'SAL-02', 'name': 'Outbound SDR Agent', 'doctrine': 'Génération continue de rendez-vous qualifiés.'},
        {'id': 'SAL-03', 'name': 'Sales Proposal Architect', 'doctrine': 'Offres percutantes alignées sur les besoins du client.'},
        {'id': 'SAL-04', 'name': 'Objection Handling Specialist', 'doctrine': 'Transformer chaque objection en opportunité de closing.'},
        {'id': 'SAL-05', 'name': 'Account Executive & Closing Agent', 'doctrine': 'Maximiser le win-rate et raccourcir les cycles.'},
        {'id': 'SAL-06', 'name': 'CRM & Pipeline Sync Agent', 'doctrine': 'Visibilité et hygiène CRM irréprochables.'},
        {'id': 'SAL-07', 'name': 'Account-Based Marketing Specialist', 'doctrine': 'Infiltration et conversion stratégique des grands comptes.'},
        {'id': 'SAL-08', 'name': 'Customer Expansion & Upsell Agent', 'doctrine': 'Maximiser la valeur de vie client (LTV).'}
    ]
}