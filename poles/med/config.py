POLE_CONFIG = {
    'ID': 'MED',
    'NAME': 'MÉDIAS, CONTENUS MULTIMODAUX & BRANDING',
    'MAIN_MODEL': 'google/gemma-4-26b-a4b',
    'FALLBACK_MODEL': 'gemini-3.1-flash-lite',
    'SUBAGENTS': [
        {
            'ID': 'MED-01',
            'NAME': 'Video Script & Storyboard Creator',
            'DESCRIPTION': 'Conception de scripts vidéo, storyboards pour YouTube, VSL et réseaux sociaux.',
            'DOCTRINE': 'Récit percutant et rétention visuelle maximale.'
        },
        {
            'ID': 'MED-02',
            'NAME': 'AI Image & Brand Assets Generator',
            'DESCRIPTION': 'Génération et direction artistique d'images, bannières et visuels de marque via AI.',
            'DOCTRINE': 'Identité visuelle haute définition et cohérente.'
        },
        {
            'ID': 'MED-03',
            'NAME': 'Podcast & Audio Content Producer',
            'DESCRIPTION': 'Scripting, édition audio et génération de contenus vocaux/podcasts.',
            'DOCTRINE': 'Qualité sonore et clarté éditoriale irréprochables.'
        },
        {
            'ID': 'MED-04',
            'NAME': 'Content Localization & Translation Agent',
            'DESCRIPTION': 'Adaptation multilingue, traduction contextuelle et localisation culturelle du contenu.',
            'DOCTRINE': 'Localisation fluide sans perte de nuance.'
        },
        {
            'ID': 'MED-05',
            'NAME': 'Infographic & Data Visualization Designer',
            'DESCRIPTION': 'Transformation de données complexes en infographies et visuels clairs.',
            'DOCTRINE': 'Rendre la donnée complexe immédiatement compréhensible.'
        },
        {
            'ID': 'MED-06',
            'NAME': 'Brand Guidelines & Tone Enforcement',
            'DESCRIPTION': 'Contrôle du ton, du style et du respect de la charte graphique sur l'ensemble des médias.',
            'DOCTRINE': 'Cohérence de marque absolue sur tous les canaux.'
        },
        {
            'ID': 'MED-07',
            'NAME': 'Interactive Media & Document Generator',
            'DESCRIPTION': 'Génération de rapports interactifs, présentations PDF et e-books marketing via FPDF/outils dédiés.',
            'DOCTRINE': 'Supports de présentation professionnels et engageants.'
        },
        {
            'ID': 'MED-08',
            'NAME': 'Content Archiving & Asset Manager',
            'DESCRIPTION': 'Structuration, indexation et archivage des médias dans la médiathèque de l'Usine Agentique.',
            'DOCTRINE': 'Gestion d'actifs média ordonnée et réutilisable.'
        }
    ]
}