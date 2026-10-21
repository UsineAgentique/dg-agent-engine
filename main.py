from e2b_code_interpreter import CodeInterpreter
import os

E2B_API_KEY = os.getenv('E2B_API_KEY')

def execute_python_code_e2b(code: str, **kwargs) -> str:
    try:
        if E2B_API_KEY and CodeInterpreter:
            with CodeInterpreter(api_key=E2B_API_KEY) as sandbox:
                execution = sandbox.notebook.exec_cell(code)
                logs_list = execution.logs.stdout if execution.logs and execution.logs.stdout else []
                logs_text = "\n".join(logs_list) if logs_list else "Aucun log."
                error_text = str(execution.error) if execution.error else "Aucune erreur."
                return f"Résultats Sandbox E2B:\nLogs: {logs_text}\nErreurs: {error_text}"
        else:
            local_scope = {}
            exec(code, {}, local_scope)
            return f"Exécution locale réussie (E2B non actif): {local_scope}"
    except Exception as e:
        return f"ERREUR EXÉCUTION SANDBOX: {str(e)}"

MODEL_CATALOG = {
    "AMAL_DG": {
        "primary": "openrouter/deepseek/deepseek-chat",
        "fallback": "openrouter/anthropic/claude-3.5-sonnet"
    },
    "TECH": {
        "primary": "openrouter/qwen/qwen-2.5-coder-32b-instruct",
        "fallback": "openrouter/deepseek/deepseek-r1"
    },
    "GOV": {
        "primary": "openrouter/thudm/glm-4-9b-chat",
        "fallback": "openrouter/anthropic/claude-3.5-sonnet"
    },
    "FIN": {
        "primary": "openrouter/anthropic/claude-3.5-sonnet",
        "fallback": "groq/llama-3.3-70b-versatile"
    },
    "RET": {
        "primary": "openrouter/anthropic/claude-3.5-sonnet",
        "fallback": "groq/llama-3.3-70b-versatile"
    }
}