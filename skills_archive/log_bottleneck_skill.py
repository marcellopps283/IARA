import os
import json

BOTTLENECKS_FILE = os.path.expanduser("~/Kitty_Shadow/GARGALOS.md")

"""
Skill: log_bottleneck
Description: Módulo do Scavenger Protocol. A IA registra ativamente algo que não consegue fazer por falta de ferramentas, permitindo que o loop de madrugada pesquise soluções.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "log_bottleneck",
            "description": "Log missing tools or capabilities so Kitty can research them during Scavenger Protocol (night loop).",
            "parameters": {
                "type": "object",
                "properties": {
                    "missing_capability": {
                        "type": "string",
                        "description": "Action you failed to perform (e.g., 'Read PDF metadata')."
                    },
                    "suggested_approach": {
                        "type": "string",
                        "description": "Search keywords for DuckDuckGo (e.g., 'python free library mp3 metadata extract')."
                    }
                },
                "required": ["missing_capability", "suggested_approach"]
            }
        }
    }

async def execute(kwargs):
    capability = kwargs.get("missing_capability")
    search_terms = kwargs.get("suggested_approach")
    
    if not capability or not search_terms:
        return "Erro: Parâmetros obrigatórios ausentes."
        
    try:
        os.makedirs(os.path.dirname(BOTTLENECKS_FILE), exist_ok=True)
        # Salva em formato estruturado (JSON por linha) para o Scavenger ler fácil no Python
        entry = json.dumps({
            "status": "PENDENTE_PESQUISA",
            "capability": capability,
            "search_terms": search_terms
        })
        
        with open(BOTTLENECKS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{entry}\n")
            
        return f"Gargalo registrado com sucesso no GARGALOS.md! Eu procurarei uma solução para '{capability}' no DuckDuckGo durante a alta madrugada."
    except Exception as e:
        return f"Falha ao escrever no GARGALOS.md: {e}"
