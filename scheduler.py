"""
scheduler.py — Agência Autônoma (Background Scheduler)
Sistema nativo em Pure-Python/Asyncio para rodar tarefas sem input humano.
Suporta cronjobs do tipo "HH:MM" ou de intervalos "interval:15m".
"""

import asyncio
import logging
from datetime import datetime, timedelta

import core
import hooks
import web_search
import config

logger = logging.getLogger("scheduler")

async def execute_action(job: dict, send_message_fn):
    """Executa a ação correspondente do job mapeado e despacha as notificações ativas."""
    action = job["action"]
    params = job.get("params", {})
    job_name = job["name"]
    
    logger.info(f"⚙️ Executando Job Autônomo '{job_name}' (Ação: {action})")
    
    try:
        if action == "morning_briefing":
            weather = await core.get_weather()
            tasks_db = await core._get_all_tasks() # Acesso aos TODOs salvos na task_state
            
            pending_tasks = [t for t in tasks_db if t["status"] in ("pending", "in_progress")]
            task_str = "\n".join([f"- #{t['id']}: {t['description']} ({t['status']})" for t in pending_tasks]) if pending_tasks else "Nenhuma pendência."
            
            news = await web_search.web_search("principais noticias tecnologia globo g1 the verge hoje br", max_results=3)
            
            msg = f"🌅 **IARA Morning Briefing**\n\n"
            msg += f"🌤️ **Clima Atual:**\n{weather}\n\n"
            msg += f"📋 **Tarefas Pendentes:**\n{task_str}\n\n"
            msg += f"📰 **Giro de Notícias da Manhã:**\n{news[:600]}...\n\n"
            msg += "Tenha um dia super produtivo! ☕"
            
            await send_message_fn(msg)
            
        elif action == "session_end_hook":
            from llm_router import LLMRouter
            router = LLMRouter()
            result = await hooks.on_session_end(router)
            if result:
                await send_message_fn(f"🧠 **Reflexão Noturna (Session End Hook)**\n\n{result}")

        elif action == "memory_consolidation":
            # Consolida a memory em background (apagar working e destilar episodic/core)
            await core.consolidate_working_memory()
            # Não emite notificação para manter silencioso, ou emite apenas em log
            logger.info("🧹 Memory Consolidation concluída via Job")

        elif action == "custom_search":
            query = params.get("query", "noticias importantes")
            result = await web_search.web_search_deep(query)
            msg = f"🔍 **Relatório de Pesquisa Autônoma: '{query}'**\n\n{result[:1500]}..."
            await send_message_fn(msg)
            
        else:
            logger.warning(f"⚠️ Ação desconhecida do job '{job_name}': {action}")

    except Exception as e:
        logger.error(f"❌ Erro ao executar job '{job_name}' (action={action}): {e}")

def should_run(job: dict, current_time: datetime) -> bool:
    """Calcula se um job está no momento de ser disparado dado o cron setado no BD."""
    cron = job["cron"]
    
    # Se last_run for nulo, vamos preencher pra não falhar a lógica
    last_run_str = job.get("last_run")
    last_run = datetime.fromisoformat(last_run_str) if last_run_str else None
    
    if cron.startswith("interval:"):
        # Relativo (ex: "interval:15m")
        try:
            minutes = int(cron.replace("interval:", "").replace("m", ""))
            if not last_run:
                return True
            if current_time >= last_run + timedelta(minutes=minutes):
                return True
        except ValueError:
            logger.error(f"Cron de intervalo inválido no job '{job['name']}': {cron}")
        return False
        
    elif ":" in cron:
        # Absoluto (HH:MM diário)
        try:
            hour, minute = map(int, cron.split(":"))
            
            # Já rodou hoje?
            if last_run and last_run.date() == current_time.date():
                return False
                
            # A hora atual é igual ou passou da hora marcada pro dia de hoje?
            if current_time.hour > hour or (current_time.hour == hour and current_time.minute >= minute):
                return True
        except ValueError:
            logger.error(f"Cron de horário absoluto inválido no job '{job['name']}': {cron}")
        return False
        
    return False

async def start_scheduler(send_message_fn):
    """
    Loop eterno isolado que gerencia a Agência Autônoma.
    Injetamos 'send_message_fn' como Callback para não ter Circular Imports no telegram_bot.
    """
    logger.info("⏱️ Iniciando Background Scheduler da IARA (Agência Autônoma)")
    
    while True:
        try:
            jobs = await core.get_all_scheduled_jobs()
            now = datetime.now()
            
            for job in jobs:
                if not job.get("enabled"):
                    continue
                    
                if should_run(job, now):
                    # Dispara de forma solta para não travar o loop pros outros jobs
                    asyncio.create_task(execute_action(job, send_message_fn))
                    await core.update_job_last_run(job["id"])
                    
        except Exception as e:
            logger.error(f"Erro Crítico no loop do scheduler: {e}")
            
        await asyncio.sleep(60) # Pulso regular de 1 minuto
