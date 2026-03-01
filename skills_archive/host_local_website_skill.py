import os
import json
from transport import TransportClient

"""
Skill: host_local_website
Description: Pede ao Moto G4 (Light Worker) para servir uma pasta HTTP local para que o usuário possa visualizar Dashboards ou GUIs projetados no Termux sem gastar bateria do S21 Ultra primário.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "host_local_website",
            "description": "Start a minimal HTTP server on the Moto G4 (Light Worker) to serve HTML dashboards or UI components over the local network.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "Name of the target dashboard folder inside ~/Kitty_Shadow/dashboards (e.g., 'trading_panel', 'system_monitor')."
                    },
                    "html_content": {
                        "type": "string",
                        "description": "The raw HTML/JS/CSS content of index.html to create/override inside that folder before hosting."
                    }
                },
                "required": ["folder_name", "html_content"]
            }
        }
    }

async def execute(kwargs):
    folder_name = kwargs.get("folder_name")
    html_content = kwargs.get("html_content")
    
    if not folder_name or not html_content:
        return "Erro: 'folder_name' e 'html_content' obrigatórios."

    light_worker_ip = os.getenv("LIGHT_WORKER_IP", "127.0.0.1")
    target_port = 5558 # Moto G4 Harpia
    
    payload = {
        "type": "host_dashboard",
        "folder": folder_name,
        "content": html_content
    }
    
    try:
        print(f"🪶 [LightWorker] Invocando Mártir Moto G4 para hospedar GUI: {folder_name}")
        client = TransportClient()
        response = await client.invoke_agent(light_worker_ip, target_port, payload)
        
        return f"Retorno do Moto G4 (Web Server):\n{json.dumps(response, indent=2)}"
    except Exception as e:
        return f"Falha ao contatar Mártir (Moto G4) na porta {target_port}: {e}"
