import os

SOUL_FILE = os.path.expanduser("~/Kitty_Shadow/SOUL_RULES.md")

"""
Skill: update_soul
Description: Módulo do Self-Improving Agent. Permite que a IA salve regras de aprendizado rígidas após corrigir bugs difíceis, criando reflexos no sistema.
"""

def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "save_soul_rule",
            "description": "Save an evolutionary system rule or software engineering guideline to SOUL_RULES.md (e.g., after fixing a bug) to prevent future mistakes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule": {
                        "type": "string",
                        "description": "The golden rule learned. Be concise (e.g., 'Never use os.system, use subprocess.run')."
                    }
                },
                "required": ["rule"]
            }
        }
    }

async def execute(kwargs):
    rule = kwargs.get("rule")
    if not rule:
        return "Erro: regra vazia."
        
    try:
        os.makedirs(os.path.dirname(SOUL_FILE), exist_ok=True)
        # Modo append para acumular aprendizados
        with open(SOUL_FILE, "a", encoding="utf-8") as f:
            f.write(f"- {rule}\n")
        return f"Regra evolucionária salva no SOUL_RULES.md com sucesso: {rule}"
    except Exception as e:
        return f"Falha ao escrever SOUL_RULES: {e}"
