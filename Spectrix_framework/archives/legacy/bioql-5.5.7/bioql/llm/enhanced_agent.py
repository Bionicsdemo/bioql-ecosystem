"""
Enhanced BioQL Agent - Versión mejorada con más tools
======================================================
"""

import re
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any
import requests


class EnhancedBioQLAgent:
    """Agent wrapper con capacidades extendidas de tools."""

    # Tools disponibles
    TOOLS = {
        "read_file": "Lee contenido de un archivo",
        "write_file": "Escribe contenido a un archivo",
        "edit_file": "Edita un archivo existente",
        "run_bioql": "Ejecuta código BioQL",
        "run_python": "Ejecuta código Python",
        "run_shell": "Ejecuta comando shell",
        "search_code": "Busca en el código (grep)",
        "list_files": "Lista archivos en directorio",
    }

    def __init__(self, model_endpoint: str, workspace: str = None):
        """
        Args:
            model_endpoint: URL del modelo BioQL
            workspace: Directorio de trabajo (default: current dir)
        """
        self.endpoint = model_endpoint
        self.workspace = Path(workspace or ".").absolute()
        self.session_history = []

    def execute(self, user_request: str, api_key: str, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Ejecuta solicitud del usuario en múltiples iteraciones si es necesario.

        Args:
            user_request: Solicitud del usuario
            api_key: API key de BioQL
            max_iterations: Máximo número de iteraciones (para evitar loops)

        Returns:
            Resultado completo con todas las acciones ejecutadas
        """
        all_actions = []
        context = f"User request: {user_request}\n\n"

        for iteration in range(max_iterations):
            # Llamar al modelo
            model_response = self._call_model(context, api_key)

            if not model_response.get("success"):
                return {
                    "success": False,
                    "error": model_response.get("error"),
                    "actions": all_actions
                }

            # Parsear y ejecutar acciones
            actions = self._extract_and_execute_actions(model_response)
            all_actions.extend(actions)

            # Verificar si está completo
            if self._is_task_complete(model_response, actions):
                return {
                    "success": True,
                    "actions": all_actions,
                    "final_response": model_response.get("text", ""),
                    "iterations": iteration + 1
                }

            # Actualizar contexto con resultados
            context += self._format_iteration_results(actions)

        return {
            "success": True,
            "actions": all_actions,
            "warning": f"Max iterations ({max_iterations}) reached",
            "iterations": max_iterations
        }

    def _call_model(self, context: str, api_key: str) -> Dict[str, Any]:
        """Llama al modelo BioQL."""
        try:
            prompt = f"""{context}

Available tools: {', '.join(self.TOOLS.keys())}

Analyze the request and respond with:
1. What tool(s) you need to use
2. The code or parameters needed
3. Your reasoning

Format:
TOOL: <tool_name>
PARAMS: <parameters or code>
REASONING: <your reasoning>
"""

            response = requests.post(self.endpoint, json={
                "api_key": api_key,
                "prompt": prompt,
                "temperature": 0.2,
                "max_length": 1000
            }, timeout=30)

            if response.status_code != 200:
                return {"success": False, "error": f"API error: {response.status_code}"}

            result = response.json()
            return {
                "success": True,
                "text": result.get("code", ""),
                "reasoning": result.get("reasoning", "")
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_and_execute_actions(self, model_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrae y ejecuta acciones del response del modelo."""
        text = model_response.get("text", "") + "\n" + model_response.get("reasoning", "")
        actions = []

        # Extraer tool calls
        tool_pattern = r'TOOL:\s*(\w+)\s*\nPARAMS:\s*(.+?)(?:\n|$)'
        matches = re.finditer(tool_pattern, text, re.DOTALL)

        for match in matches:
            tool_name = match.group(1)
            params = match.group(2).strip()

            action_result = self._execute_tool(tool_name, params)
            actions.append({
                "tool": tool_name,
                "params": params,
                "result": action_result.get("output"),
                "success": action_result.get("success"),
                "error": action_result.get("error")
            })

        # Si no hay tool calls explícitos, inferir del contenido
        if not actions:
            actions = self._infer_actions(text)

        return actions

    def _execute_tool(self, tool_name: str, params: str) -> Dict[str, Any]:
        """Ejecuta un tool específico."""
        try:
            if tool_name == "read_file":
                file_path = self.workspace / params.strip()
                with open(file_path, 'r') as f:
                    content = f.read()
                return {"success": True, "output": content}

            elif tool_name == "write_file":
                # Format: filename|content
                parts = params.split('|', 1)
                if len(parts) != 2:
                    return {"success": False, "error": "Invalid format. Use: filename|content"}

                file_path = self.workspace / parts[0].strip()
                content = parts[1].strip()

                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content)

                return {"success": True, "output": f"Wrote to {file_path}"}

            elif tool_name == "edit_file":
                # Format: filename|old_content|new_content
                parts = params.split('|', 2)
                if len(parts) != 3:
                    return {"success": False, "error": "Invalid format"}

                file_path = self.workspace / parts[0].strip()
                old_content = parts[1].strip()
                new_content = parts[2].strip()

                with open(file_path, 'r') as f:
                    current = f.read()

                if old_content not in current:
                    return {"success": False, "error": "Old content not found"}

                updated = current.replace(old_content, new_content)
                with open(file_path, 'w') as f:
                    f.write(updated)

                return {"success": True, "output": f"Edited {file_path}"}

            elif tool_name == "run_bioql":
                # Ejecutar código BioQL
                temp_file = "/tmp/bioql_temp.bioql"
                with open(temp_file, 'w') as f:
                    f.write(params)

                result = subprocess.run(
                    ["bioql", "quantum", "execute", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }

            elif tool_name == "run_python":
                temp_file = "/tmp/bioql_agent_python.py"
                with open(temp_file, 'w') as f:
                    f.write(params)

                result = subprocess.run(
                    ["python3", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }

            elif tool_name == "run_shell":
                result = subprocess.run(
                    params,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.workspace
                )

                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }

            elif tool_name == "search_code":
                # Format: pattern|path
                parts = params.split('|')
                pattern = parts[0].strip()
                path = parts[1].strip() if len(parts) > 1 else "."

                result = subprocess.run(
                    ["grep", "-r", "-n", pattern, path],
                    capture_output=True,
                    text=True,
                    cwd=self.workspace
                )

                return {"success": True, "output": result.stdout}

            elif tool_name == "list_files":
                path = self.workspace / params.strip() if params.strip() else self.workspace
                files = list(path.glob("*"))
                file_list = "\n".join([f.name for f in files])

                return {"success": True, "output": file_list}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _infer_actions(self, text: str) -> List[Dict[str, Any]]:
        """Infiere acciones del texto cuando no hay tool calls explícitos."""
        actions = []

        # Detectar código BioQL
        bioql_pattern = r'```bioql\n(.+?)\n```'
        for match in re.finditer(bioql_pattern, text, re.DOTALL):
            code = match.group(1)
            result = self._execute_tool("run_bioql", code)
            actions.append({
                "tool": "run_bioql",
                "params": code,
                "result": result.get("output"),
                "success": result.get("success"),
                "inferred": True
            })

        # Detectar código Python
        python_pattern = r'```python\n(.+?)\n```'
        for match in re.finditer(python_pattern, text, re.DOTALL):
            code = match.group(1)
            result = self._execute_tool("run_python", code)
            actions.append({
                "tool": "run_python",
                "params": code,
                "result": result.get("output"),
                "success": result.get("success"),
                "inferred": True
            })

        return actions

    def _is_task_complete(self, model_response: Dict[str, Any], actions: List[Dict[str, Any]]) -> bool:
        """Determina si la tarea está completa."""
        text = model_response.get("text", "").lower()

        # Indicadores de completitud
        complete_indicators = ["done", "complete", "finished", "success"]
        if any(indicator in text for indicator in complete_indicators):
            return True

        # Si no hay acciones y el modelo respondió, asumir completo
        if not actions and text:
            return True

        # Si todas las acciones fueron exitosas
        if actions and all(a.get("success") for a in actions):
            return True

        return False

    def _format_iteration_results(self, actions: List[Dict[str, Any]]) -> str:
        """Formatea resultados de una iteración para el próximo contexto."""
        if not actions:
            return "\nNo actions were taken.\n"

        result_text = "\nActions taken:\n"
        for i, action in enumerate(actions, 1):
            result_text += f"{i}. {action['tool']}: "
            if action.get('success'):
                result_text += f"Success - {action.get('result', '')[:100]}\n"
            else:
                result_text += f"Failed - {action.get('error', '')}\n"

        return result_text + "\n"


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """CLI para usar el agent."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_agent.py '<request>' [--workspace <path>]")
        print("\nExample:")
        print("  python enhanced_agent.py 'Create a Bell state with BioQL'")
        sys.exit(1)

    user_request = sys.argv[1]
    workspace = "."

    if "--workspace" in sys.argv:
        idx = sys.argv.index("--workspace")
        workspace = sys.argv[idx + 1]

    # Configuración
    model_endpoint = "https://spectrix--bioql-inference-deepseek-generate-code.modal.run"
    api_key = "bioql_test_870ce7ae"

    # Crear y ejecutar agent
    agent = EnhancedBioQLAgent(model_endpoint, workspace)

    print(f"🤖 BioQL Agent executing: {user_request}")
    print("=" * 60)

    result = agent.execute(user_request, api_key)

    if result["success"]:
        print(f"\n✅ Task completed in {result['iterations']} iteration(s)")
        print(f"\n📋 Actions taken ({len(result['actions'])}):")
        for i, action in enumerate(result['actions'], 1):
            status = "✓" if action.get('success') else "✗"
            print(f"  {i}. {status} {action['tool']}")
            if action.get('error'):
                print(f"     Error: {action['error']}")
    else:
        print(f"\n❌ Task failed: {result.get('error')}")

    # Guardar log
    log_file = Path(workspace) / "bioql_agent.log"
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Request: {user_request}\n")
        f.write(f"Result: {json.dumps(result, indent=2)}\n")


if __name__ == "__main__":
    main()
