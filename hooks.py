"""
hooks.py — Ecossistema Baseado em Eventos da IARA v2
Estes hooks formam a espinha dorsal da arquitetura reativa,
garantindo segurança e aprendizado contínuo.
"""

import asyncio
import logging
from datetime import datetime

import core
import config

logger = logging.getLogger("hooks")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Segurança (Defesa)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def before_shell_execution(command: str) -> bool:
    """Impede comandos fatais no bash isolado."""
    forbidden = ["rm -rf", "mkfs", "dd ", "> /dev/sda", "chmod 777 -R /", "poweroff"]
    cmd_lower = command.lower()
    
    if any(f in cmd_lower for f in forbidden):
        logger.critical(f"🛑 [Red Team] Comando fatal bloqueado: {command}")
        return False
    return True

async def before_submit_prompt(prompt_text: str) -> str:
    """Impede o vazamento de chaves sensíveis nos prompts enviados para a nuvem."""
    import re
    # Regex para pegar sk-, ghp_, ou possíveis JWTs óbvios
    patterns = [r"sk-[a-zA-Z0-9]{40,}", r"ghp_[a-zA-Z0-9]{36}"]
    
    sanitized = prompt_text
    for p in patterns:
        sanitized = re.sub(p, "[REDACTED_CREDENTIAL]", sanitized)
        
    if sanitized != prompt_text:
        logger.warning("🛡️ [Red Team] Credenciais ofuscadas antes de enviar ao LLM.")
        
    return sanitized

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ciclo de Vida & Evolução Contínua
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def on_session_start(chat_id: int):
    """Executado na primeira mensagem do dia/sessão."""
    logger.info("🌅 Iniciando nova sessão. Preparando banco e limpando caches temporários.")
    # Limpa tarefas estáticas pendentes antigas
    async with __import__('aiosqlite').connect(str(config.DB_PATH)) as db:
        await db.execute("UPDATE tasks_state SET status = 'pending' WHERE status = 'in_progress'")
        await db.execute("UPDATE swarm_jobs SET status = 'pending' WHERE status = 'processing'")
        await db.commit()

async def on_pre_compact(working_memory: list):
    """Executado imediatamente antes da compactação da working memory."""
    logger.info(f"📦 Pre-Compact Hook disparado! Memória com {len(working_memory)} itens.")
    # Pode ser usado para extrair metadados matemáticos de uso antes do log virar resumo.

async def on_session_end(chat_id: int, router: "LLMRouter"):
    """
    Instintos (Fase 5): Chamado ao final do fechamento diário ou ociosidade longa.
    Analisa os episódios não-processados para extrair "Instintos" vitais (o que funcionou/falhou).
    """
    logger.info("🌙 Session End. Extraindo INSTINTOS da sessão atual...")
    from llm_router import LLMRouter
    
    episodes = await core.get_recent_episodes(limit=5)
    if not episodes:
        return
        
    history = "\n".join([ep['summary'] for ep in episodes])
    
    prompt = [
        {"role": "system", "content": (
            "Você é o subconsciente da inteligência artificial. "
            "Avalie os logs de interação e extraia 1 REGRA DE OURO TÉCNICA (Instinto) baseada no que deu certo ou na reclamação do usuário.\n"
            "Retorne a regra e a CLAREZA DA REGRA no formato: [Clareza: 0.95] A interface não deve ter popups modais."
        )},
        {"role": "user", "content": f"Logs:\n{history}"}
    ]
    
    # Roda pelo Cerebras/Kimi (chat_fast/consolidation)
    result = await router.generate(prompt, task_type="consolidation")
    if result and isinstance(result, str) and "[Clareza:" in result:
        # Salva o instinto na core_memory como 'instinto' (não preferência isolada, será compilado depois)
        await core.save_core_fact("instinto", result.strip(), confidence=1.0)
        logger.info(f"✨ Instinto Gerado: {result.strip()}")
