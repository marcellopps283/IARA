import os
import json
from transport import TransportClient

"""
Skill: composio_bridge
Description: Ponte para o SDK da Composio que permite delegar autenticação OAuth e execução de ações SaaS (GitHub, Gmail, Notion) para a nuvem.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "composio_execute_action",
            "description": "Execute a SaaS action (e.g., GitHub, Gmail, Google Calendar) using Composio. Abstracts away OAuth and local API keys.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_name": {
                        "type": "string",
                        "description": "The exact uppercase action name from Composio (e.g., 'GITHUB_GET_STARRED_REPOSITORIES', 'GMAIL_SEND_EMAIL')."
                    },
                    "action_params": {
                        "type": "string",
                        "description": "A JSON-formatted string containing the parameters required for the action."
                    }
                },
                "required": ["action_name", "action_params"]
            }
        }
    }

async def execute(kwargs):
    action_name = kwargs.get("action_name")
    params_str = kwargs.get("action_params", "{}")
    
    try:
        json.loads(params_str)
    except json.JSONDecodeError:
        return "Erro: action_params deve ser um JSON válido."

    heavy_worker_ip = os.getenv("HEAVY_WORKER_IP", "127.0.0.1")
    target_port = 5556 # S21 FE
    
    payload = {
        "type": "composio_execute_action",
        "action_name": action_name,
        "action_params": params_str
    }
    
    try:
        print(f"🔗 [Composio] Delegando action '{action_name}' para o S21 FE...")
        client = TransportClient()
        response = await client.invoke_agent(heavy_worker_ip, target_port, payload, timeout=120)
        return f"Retorno do S21 FE (Composio):\n{json.dumps(response, indent=2)}"
    except Exception as e:
        return f"Falha na delegação Composio para S21 FE: {e}"
