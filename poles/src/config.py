POLE_CONFIG = {
    "SRC": {
        "name": "SOURCING, DATA MINING & WEB SCRAPING",
        "main_model": "google/gemma-4-31b",
        "fallback_model": "openai/gpt-oss-20b",
        "subagents": {
            "SRC-01": {
                "name": "Web Scraping & Extraction Agent",
                "doctrine": "Extraction propre, rapide et sans perte de données."
            },
            "SRC-02": {
                "name": "Market Intelligence & Data Miner",
                "doctrine": "Données exploitables et insights de marché précis."
            },
            "SRC-03": {
                "name": "Competitor Intelligence Tracker",
                "doctrine": "Savoir ce que font les concurrents avant qu'ils ne le lancent."
            },
            "SRC-04": {
                "name": "API Integration & Connector Agent",
                "doctrine": "Flux de données continus et sécurisés."
            },
            "SRC-05": {
                "name": "Database Ingestion & ETL Specialist",
                "doctrine": "Zéro donnée corrompue en base."
            },
            "SRC-06": {
                "name": "Social Listening & Sentiment Miner",
                "doctrine": "Comprendre la voix et les frustrations du marché."
            },
            "SRC-07": {
                "name": "Geospatial & Property Sourcing",
                "doctrine": "Localisation et ciblage foncier chirurgical."
            },
            "SRC-08": {
                "name": "Data Quality & Validation Auditor",
                "doctrine": "Qualité de données irréprochable à chaque niveau."
            }
        }
    }
}