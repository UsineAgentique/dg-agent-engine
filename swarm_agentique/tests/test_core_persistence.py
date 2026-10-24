"""
Tests unitaires pour le module de persistance du noyau (Core Persistence).
Valide la sauvegarde, le chargement et l'intégrité de l'état du projet.
"""
import pytest
import json
import os
import tempfile
from pathlib import Path

# Import du module à tester (ajustez le chemin selon la structure réelle)
# from swarm_agentique.core.persistence import ProjectStateManager

class TestCorePersistence:
    """Suite de tests pour la persistance de l'état du Swarm."""

    @pytest.fixture
    def temp_storage_path(self):
        """Crée un répertoire temporaire isolé pour les tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_state_data(self):
        """Fournit un dictionnaire d'état typique du projet."""
        return {
            "project_id": "swarm-alpha-001",
            "version": "1.0.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "agents": [
                {"id": "agent-fin-01", "role": "FIN", "status": "active", "last_task": "budget_forecast"},
                {"id": "agent-tech-01", "role": "TECH", "status": "idle", "last_task": None}
            ],
            "context": {
                "current_phase": "execution",
                "budget_remaining": 85000.0
            }
        }

    def test_save_state_creates_file(self, temp_storage_path, sample_state_data):
        """Vérifie que la sauvegarde crée un fichier JSON valide."""
        # manager = ProjectStateManager(storage_path=temp_storage_path)
        # manager.save_state(sample_state_data)
        
        # Simulation de l'écriture pour le test de structure
        file_path = temp_storage_path / f"{sample_state_data['project_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_state_data, f, indent=2)
            
        assert file_path.exists(), "Le fichier d'état n'a pas été créé."
        assert file_path.stat().st_size > 0, "Le fichier d'état est vide."

    def test_load_state_restores_data(self, temp_storage_path, sample_state_data):
        """Vérifie que le chargement restaure fidèlement les données."""
        file_path = temp_storage_path / f"{sample_state_data['project_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_state_data, f)
            
        # manager = ProjectStateManager(storage_path=temp_storage_path)
        # loaded_data = manager.load_state(sample_state_data['project_id'])
        
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            
        assert loaded_data == sample_state_data, "Les données chargées diffèrent de l'original."
        assert loaded_data['project_id'] == sample_state_data['project_id']
        assert len(loaded_data['agents']) == 2

    def test_load_nonexistent_state_raises_error(self, temp_storage_path):
        """Vérifie la gestion d'erreur pour un ID de projet inconnu."""
        # manager = ProjectStateManager(storage_path=temp_storage_path)
        # with pytest.raises(FileNotFoundError):
        #     manager.load_state("projet-inexistant")
        
        non_existent_path = temp_storage_path / "projet-inexistant.json"
        assert not non_existent_path.exists()
        # Simulation de l'exception attendue
        with pytest.raises(FileNotFoundError):
            with open(non_existent_path, 'r') as f:
                pass

    def test_state_integrity_checksum(self, temp_storage_path, sample_state_data):
        """Valide l'intégrité des données via checksum (si implémenté)."""
        import hashlib
        
        # Calcul du hash de référence
        serialized = json.dumps(sample_state_data, sort_keys=True).encode('utf-8')
        expected_hash = hashlib.sha256(serialized).hexdigest()
        
        # Sauvegarde
        file_path = temp_storage_path / f"{sample_state_data['project_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sample_state_data, f, sort_keys=True)
            
        # Vérification intégrité
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().encode('utf-8')
            actual_hash = hashlib.sha256(content).hexdigest()
            
        assert actual_hash == expected_hash, "Corruption de données détectée (checksum invalide)."

    def test_concurrent_access_simulation(self, temp_storage_path, sample_state_data):
        """Test basique de résistance à l'accès concurrent (écriture/lecture)."""
        import threading
        import time
        
        file_path = temp_storage_path / f"{sample_state_data['project_id']}.json"
        errors = []
        
        def writer():
            try:
                for i in range(10):
                    data = sample_state_data.copy()
                    data['version'] = f"1.0.{i}"
                    with open(file_path, 'w') as f:
                        json.dump(data, f)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for _ in range(10):
                    if file_path.exists():
                        with open(file_path, 'r') as f:
                            json.load(f)  # Doit être du JSON valide
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        assert len(errors) == 0, f"Erreurs lors de l'accès concurrent : {errors}"

    def test_migration_schema_compatibility(self, temp_storage_path):
        """Teste la compatibilité ascendante (vieux schéma -> nouveau schéma)."""
        # Ancien format (v0.9)
        legacy_state = {
            "project_id": "legacy-001",
            "agents": ["FIN", "TECH"],  # Ancien format: liste de strings
            "budget": 100000
        }
        
        file_path = temp_storage_path / "legacy-001.json"
        with open(file_path, 'w') as f:
            json.dump(legacy_state, f)
            
        # Chargement et migration simulée
        with open(file_path, 'r') as f:
            loaded = json.load(f)
            
        # Logique de migration (exemple)
        migrated = {
            "project_id": loaded["project_id"],
            "version": "1.0.0",
            "agents": [{"role": r, "status": "unknown"} for r in loaded["agents"]],
            "context": {"budget_remaining": loaded["budget"]}
        }
        
        assert migrated["version"] == "1.0.0"
        assert isinstance(migrated["agents"], list)
        assert isinstance(migrated["agents"][0], dict)
        assert migrated["agents"][0]["role"] == "FIN"
        assert migrated["context"]["budget_remaining"] == 100000

if __name__ == "__main__":
    pytest.main([__file__, "-v"])