def execute_python_code_e2b(code: str, **kwargs) -> str:
    try:
        if E2B_API_KEY and Sandbox:
            with Sandbox.create() as sandbox:
                execution = sandbox.run_code(code)
                logs_text = str(execution.logs) if execution.logs else "Aucun log."
                error_text = str(execution.error) if execution.error else "Aucune erreur."
                return f"Résultats Sandbox E2B:\nLogs: {logs_text}\nErreurs: {error_text}"
        else:
            local_scope = {}
            exec(code, {}, local_scope)
            return f"Exécution locale réussie (E2B non actif): {local_scope}"
    except Exception as e:
        return f"ERREUR EXÉCUTION SANDBOX: {str(e)}"