from transport import TransportClient
import os
import json

"""
Skill: delegate_shadow
Description: Ferramenta A2A (Agent-to-Agent) que permite a Kitty enviar códigos perigosos, scripts Python temporários ou comandos de shell para serem executados no ambiente forjado (Sandbox/PRoot) da Kitty_Shadow.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "delegate_to_shadow",
            "description": "Send Python or Shell code to execute in an isolated Sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code_to_run": {
                        "type": "string",
                        "description": "Raw Python or Shell code."
                    },
                    "language": {
                        "type": "string",
                        "enum": ["python", "bash"],
                        "description": "Programming language ('python' or 'bash')."
                    },
                    "tier": {
                        "type": "string",
                        "enum": ["heavy", "light"],
                        "description": "Target hardware tier. 'light' for simple I/O/scraping. 'heavy' for dense processing."
                    }
                },
                "required": ["code_to_run", "language", "tier"]
            }
        }
    }

async def execute(kwargs):
    code_to_run = kwargs.get("code_to_run")
    language = kwargs.get("language")
    tier = kwargs.get("tier", "heavy")
    
    # Resolvendo o roteamento hierárquico Edge (AIA)
    # Valores ideais que serão injetáveis via .env
    heavy_worker_ip = os.getenv("HEAVY_WORKER_IP", "127.0.0.1")
    light_worker_ip = os.getenv("LIGHT_WORKER_IP", "127.0.0.1")
    
    if tier == "light":
        target_ip = light_worker_ip
        target_port = 5558 # Porta reservada para o Mártir (Moto G4 Harpia)
        print(f"🪶 [Tier Routing] Redirecionando payload para Light Worker (Moto G4) em {target_ip}:{target_port}")
    else:
        target_ip = heavy_worker_ip
        target_port = 5556 # Porta do S21 FE (Heavy Sandbox)
        print(f"⚙️ [Tier Routing] Redirecionando payload denso para Heavy Worker (S21 FE) em {target_ip}:{target_port}")
    
    payload = {
        "type": "execute_code",
        "language": language,
        "code": code_to_run
    }
    
    try:
        client = TransportClient()
        response = await client.invoke_agent(target_ip, target_port, payload)
        
        # O retorno é o stdout/stderr da Shadow testando o código na jaula dela
        return f"Retorno da Shadow (Sandbox): {json.dumps(response)}"
    except Exception as e:
        return f"Falha na delegação A2A para Shadow: {str(e)}"
