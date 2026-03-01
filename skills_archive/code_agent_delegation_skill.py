import os
import json
from transport import TransportClient

"""
Skill: code_agent_delegation
Description: Delega um grande objetivo (Objective) para o Heavy Worker (S21 FE), que usará o framework smolagents para baixar ferramentas do Hugging Face Hub under-the-hood, escrever código Python de forma autônoma e iterar sobre o erro até concluir a meta.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "delegate_agentic_objective",
            "description": "Delegate a complex, multi-step problem to the Heavy Worker (S21 FE). The Worker will function as an autonomous CodeAgent (smolagents), downloading necessary Hugging Face tools and writing Python code itself until the objective is reached. Use this for tasks that require trial and error.",
            "parameters": {
                "type": "object",
                "properties": {
                    "objective": {
                        "type": "string",
                        "description": "The high-level goal (e.g., 'Download AAPL stock data from Yahoo, analyze the moving average, and generate a plot image')."
                    }
                },
                "required": ["objective"]
            }
        }
    }

async def execute(kwargs):
    objective = kwargs.get("objective")
    if not objective:
        return "Erro: 'objective' obrigatório."

    heavy_worker_ip = os.getenv("HEAVY_WORKER_IP", "127.0.0.1")
    target_port = 5556 # S21 FE
    
    payload = {
        "type": "delegate_objective",
        "objective": objective
    }
    
    try:
        print(f"🤖 [CodeAgent] Invocando S21 FE para objetivo autônomo: {objective}")
        client = TransportClient()
        # Tempo de timeout massivo porque o CodeAgent pode demorar minutos para iterar
        response = await client.invoke_agent(heavy_worker_ip, target_port, payload, timeout=600)
        
        return f"Relatório do Heavy Worker (smolagents):\n{json.dumps(response, indent=2)}"
    except Exception as e:
        return f"Falha na delegação do CodeAgent para S21 FE: {e}"
