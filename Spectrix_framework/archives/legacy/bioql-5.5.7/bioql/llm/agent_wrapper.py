"""
BioQL Agent Wrapper - Convierte modelo de lenguaje en agente
==============================================================

Permite al modelo fine-tuned usar tools sin reentrenar.
"""

import re
import subprocess
from pathlib import Path


class BioQLAgent:
    """Wrapper que da capacidades de agente al modelo BioQL."""

    def __init__(self, model_endpoint):
        """
        Args:
            model_endpoint: URL del modelo BioQL fine-tuned
        """
        self.endpoint = model_endpoint
        self.conversation_history = []

    def execute(self, user_request: str, api_key: str) -> dict:
        """
        Ejecuta una solicitud del usuario usando el modelo + tools.

        Args:
            user_request: "Fix indentation in clinical_study.py"
            api_key: API key de BioQL

        Returns:
            {
                "success": bool,
                "actions_taken": [list of actions],
                "result": str,
                "code_generated": str
            }
        """
        import requests

        # 1. Generar plan con el modelo
        response = requests.post(self.endpoint, json={
            "api_key": api_key,
            "prompt": f"""You are a coding assistant. The user asked: "{user_request}"

Analyze what needs to be done and respond with:
1. Actions needed (read file, edit file, run command, etc.)
2. The code or commands to execute

Format your response as:
ACTIONS:
- [action 1]
- [action 2]

CODE:
[code here]
""",
            "include_reasoning": True,
            "temperature": 0.3,
            "max_length": 500
        })

        if response.status_code != 200:
            return {"success": False, "error": "Model API error"}

        result = response.json()
        reasoning = result.get("reasoning", "")
        code = result.get("code", "")

        # 2. Parsear acciones del reasoning
        actions = self._parse_actions(reasoning, code)

        # 3. Ejecutar acciones
        executed_actions = []
        for action in actions:
            try:
                action_result = self._execute_action(action)
                executed_actions.append({
                    "action": action,
                    "result": action_result,
                    "success": True
                })
            except Exception as e:
                executed_actions.append({
                    "action": action,
                    "error": str(e),
                    "success": False
                })

        return {
            "success": True,
            "reasoning": reasoning,
            "code_generated": code,
            "actions_taken": executed_actions
        }

    def _parse_actions(self, reasoning: str, code: str) -> list:
        """Extrae acciones del reasoning y código."""
        actions = []

        # Detectar lectura de archivos
        file_read_pattern = r'read\s+([^\s]+)'
        for match in re.finditer(file_read_pattern, reasoning.lower()):
            actions.append({"type": "read", "file": match.group(1)})

        # Detectar edición de archivos
        if "edit" in reasoning.lower() or "fix" in reasoning.lower():
            # Inferir archivo del contexto
            file_pattern = r'(\w+\.py)'
            files = re.findall(file_pattern, reasoning)
            if files:
                actions.append({"type": "edit", "file": files[0], "new_content": code})

        # Detectar ejecución de código
        if "run" in reasoning.lower() or "execute" in reasoning.lower():
            actions.append({"type": "execute", "code": code})

        # Detectar creación de archivos
        if "create" in reasoning.lower() or "write" in reasoning.lower():
            file_pattern = r'(\w+\.py)'
            files = re.findall(file_pattern, reasoning)
            if files:
                actions.append({"type": "write", "file": files[0], "content": code})

        return actions

    def _execute_action(self, action: dict):
        """Ejecuta una acción usando tools del sistema."""
        action_type = action["type"]

        if action_type == "read":
            # Leer archivo
            file_path = action["file"]
            with open(file_path, 'r') as f:
                return f.read()

        elif action_type == "write":
            # Escribir archivo
            file_path = action["file"]
            content = action["content"]
            with open(file_path, 'w') as f:
                f.write(content)
            return f"Created {file_path}"

        elif action_type == "edit":
            # Editar archivo (reemplazar contenido)
            file_path = action["file"]
            new_content = action["new_content"]

            # Backup
            backup_path = f"{file_path}.backup"
            subprocess.run(["cp", file_path, backup_path])

            # Escribir nuevo contenido
            with open(file_path, 'w') as f:
                f.write(new_content)

            return f"Edited {file_path} (backup: {backup_path})"

        elif action_type == "execute":
            # Ejecutar código Python
            code = action["code"]

            # Escribir a archivo temporal
            temp_file = "/tmp/bioql_agent_exec.py"
            with open(temp_file, 'w') as f:
                f.write(code)

            # Ejecutar
            result = subprocess.run(
                ["python3", temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout
            else:
                raise Exception(f"Execution failed: {result.stderr}")

        else:
            raise ValueError(f"Unknown action type: {action_type}")


# ============================================================================
# Uso
# ============================================================================

if __name__ == "__main__":
    # Ejemplo de uso
    agent = BioQLAgent(
        model_endpoint="https://spectrix--bioql-inference-deepseek-generate-code.modal.run"
    )

    # Caso 1: Generar código
    result = agent.execute(
        user_request="Create a Bell state using BioQL",
        api_key="bioql_test_870ce7ae"
    )

    print("Result:", result)

    # Caso 2: Fix código
    # result = agent.execute(
    #     user_request="Fix indentation in clinical_study.py",
    #     api_key="bioql_test_870ce7ae"
    # )
