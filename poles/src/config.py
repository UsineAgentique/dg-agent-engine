POLE_CONFIG = {
    "id": "SRC",
    "name": "SOURCING, DATA MINING & WEB SCRAPING",
    "main_model": "google/gemma-4-31b",
    "fallback_model": "openai/gpt-oss-20b",
    "subagents": [
        {
            "id": "SRC-01",
            "name": "Web Scraping & Extraction Agent",
            "doctrine": "Extraction propre, rapide et sans perte de données."
        },
        {
            "id": "SRC-02",
            "name": "Market Intelligence & Data Miner",
            "doctrine": "Données exploitables et insights de marché précis."
        },
        {
            "id": "SRC-03",
            "name": "Competitor Intelligence Tracker",
            "doctrine": "Savoir ce que font les concurrents avant qu'ils ne le lancent."
        },
        {
            "id": "SRC-04",
            "name": "API Integration & Connector Agent",
            "doctrine": "Flux de données continus et sécurisés."
        },
        {
            "id": "SRC-05",
            "name": "Database Ingestion & ETL Specialist",
            "doctrine": "Zéro donnée corrompue en base."
        },
        {
            "id": "SRC-06",
            "name": "Social Listening & Sentiment Miner",
            "doctrine": "Comprendre la voix et les frustrations du marché."
        },
        {
            "id": "SRC-07",
            "name": "Geospatial & Property Sourcing",
            "doctrine": "Localisation et ciblage foncier chirurgical."
        },
        {
            "id": "SRC-08",
            "name": "Data Quality & Validation Auditor",
            "doctrine": "Qualité de données irréprochable à chaque niveau."
        }
    ]
}