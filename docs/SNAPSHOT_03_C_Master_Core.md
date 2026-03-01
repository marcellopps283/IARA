
--- FILE: brain.py ---
"""
brain.py — Orquestrador principal da Iara
Ponto de entrada: recebe mensagem → classifica intent → executa tools → chama LLM → responde.
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timedelta

# Configurar logging antes de importar módulos
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("brain")

import config
import core
import web_search
import deep_research
import doc_reader
import telegram_bot
import worker_protocol
from llm_router import LLMRouter

import threading
import dashboard_api
import orchestrator


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Intent Detection — classifica o que o Criador quer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEARCH_KEYWORDS = [
    "pesquisa", "pesquisar", "busca", "buscar", "procura", "procurar",
    "search", "google", "qual o preço", "quanto custa",
    "quanto tá", "quanto está", "cotação",
    "notícia", "noticias", "news",
]

MEMORY_SAVE_KEYWORDS = [
    "lembra que", "lembre que", "memoriza", "memorize",
    "guarda isso", "salva isso", "anota isso", "não esquece",
    "grava isso", "registra",
]

MEMORY_RECALL_KEYWORDS = [
    "o que você sabe sobre mim", "o que sabe de mim",
    "o que você lembra", "o que lembra de mim",
    "minhas preferências", "meus dados",
]

WEATHER_KEYWORDS = [
    "clima", "tempo", "previsão", "vai chover", "temperatura",
    "tá frio", "tá quente", "weather", "chovendo",
]

STATUS_KEYWORDS = [
    "status", "bateria", "battery", "storage", "como tá o celular",
    "espaço", "sistema", "uptime",
]

REMINDER_KEYWORDS = [
    "me lembra", "me lembre", "me avisa", "me avise",
    "daqui a", "daqui", "lembrete", "reminder",
    "me acorda", "alarme",
]

DEEP_RESEARCH_KEYWORDS = [
    "pesquisa profunda", "pesquisa detalhada", "deep search",
    "deep research", "pesquisa completa", "analisa profundamente",
    "faz um levantamento", "investiga sobre", "investigar sobre",
    "pesquisa tudo sobre",
]

SWARM_KEYWORDS = [
    "swarm", "no swarm", "joga no swarm", "pede pro swarm",
    "manda um agente", "cria um agente", "delega pra",
    "revisa esse código", "analisa esse log",
]

CYBER_HANDS_KEYWORDS = [
    "lanterna", "ligar lanterna", "apagar lanterna", "desligar lanterna",
    "luz", "ilumina", "onde eu to", "onde eu tô", "localização",
    "localizacao", "onde nós estamos", "gps", "coordenadas",
]

# Regex para detectar URLs
URL_REGEX = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


async def classify_intent(text: str, router: LLMRouter) -> tuple[str, str | None]:
    """
    Classifica intent em 2 etapas:
    1. Keywords rápidas (sem chamar LLM)
    2. Se não bateu keyword, pede pro LLM classificar
    """
    text_lower = text.lower().strip()

    # URLs na mensagem → auto-read
    urls = URL_REGEX.findall(text)
    if urls:
        return ("url_read", urls[0])

    # Memory save
    for kw in MEMORY_SAVE_KEYWORDS:
        if kw in text_lower:
            fact = text_lower
            for k in MEMORY_SAVE_KEYWORDS:
                fact = fact.replace(k, "").strip()
            return ("save_memory", fact or text)

    # Memory recall
    for kw in MEMORY_RECALL_KEYWORDS:
        if kw in text_lower:
            return ("recall_memory", None)

    # Deep Research
    for kw in DEEP_RESEARCH_KEYWORDS:
        if kw in text_lower:
            query = text_lower
            for k in DEEP_RESEARCH_KEYWORDS:
                query = query.replace(k, "").strip()
            return ("deep_research", query or text)

    # Swarm Orchestrator (Personas Estáticas)
    for kw in SWARM_KEYWORDS:
        if kw in text_lower:
            query = text_lower
            for k in SWARM_KEYWORDS:
                query = query.replace(k, "").strip()
            return ("swarm", query or text)

    # Reminders
    for kw in REMINDER_KEYWORDS:
        if kw in text_lower:
            return ("reminder", text)

    # Weather
    for kw in WEATHER_KEYWORDS:
        if kw in text_lower:
            return ("weather", None)

    # System status
    for kw in STATUS_KEYWORDS:
        if kw in text_lower:
            return ("status", None)

    # Cyber-Mãos (Hardware control)
    for kw in CYBER_HANDS_KEYWORDS:
        if kw in text_lower:
            if any(w in text_lower for w in ["lanterna", "luz", "ilumina"]):
                is_on = not any(w in text_lower for w in ["apagar", "desligar", "off"])
                return ("flashlight", "on" if is_on else "off")
            elif any(w in text_lower for w in ["onde", "localização", "localizacao", "gps", "coordenadas"]):
                return ("location", None)

    # Search
    for kw in SEARCH_KEYWORDS:
        if kw in text_lower:
            query = text_lower
            for k in SEARCH_KEYWORDS:
                query = query.replace(k, "").strip()
            return ("search", query or text)

    # LLM classifica (rápido)
    try:
        classification = await router.generate([
            {"role": "system", "content": (
                "Classifique a intenção APENAS como SEARCH ou CHAT. "
                "SEARCH = precisa de informação atualizada da internet. "
                "CHAT = conversa normal, opinião, saudação. "
                "Responda só a palavra."
            )},
            {"role": "user", "content": text},
        ], temperature=0.0)

        if isinstance(classification, str) and "SEARCH" in classification.upper():
            logger.info(f"🤖 LLM classificou como SEARCH: {text[:50]}")
            return ("search", text)
    except Exception as e:
        logger.warning(f"⚠️ Classificação falhou: {e}")

    return ("chat", None)


def parse_reminder_time(text: str) -> tuple[str, datetime | None]:
    """
    Extrai duração/horário do texto do reminder.
    Retorna (mensagem_limpa, horário_trigger).
    """
    now = datetime.now()

    # "daqui a X minutos/horas"
    match = re.search(r'daqui\s+(?:a\s+)?(\d+)\s*(min(?:uto)?s?|hora?s?|seg(?:undo)?s?)', text, re.IGNORECASE)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        if 'hora' in unit or unit.startswith('h'):
            delta = timedelta(hours=amount)
        elif 'seg' in unit:
            delta = timedelta(seconds=amount)
        else:
            delta = timedelta(minutes=amount)

        # Limpar o texto
        msg = re.sub(r'daqui\s+(?:a\s+)?\d+\s*\S+', '', text, flags=re.IGNORECASE).strip()
        # Remover keywords do reminder
        for kw in REMINDER_KEYWORDS:
            msg = msg.replace(kw, "").strip()
        return (msg or text, now + delta)

    # "às HH:MM" ou "as HH:MM"
    match = re.search(r'[àa]s?\s+(\d{1,2})[h:](\d{2})?', text, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        target = now.replace(hour=hour, minute=minute, second=0)
        if target < now:
            target += timedelta(days=1)

        msg = re.sub(r'[àa]s?\s+\d{1,2}[h:]\d{0,2}', '', text, flags=re.IGNORECASE).strip()
        for kw in REMINDER_KEYWORDS:
            msg = msg.replace(kw, "").strip()
        return (msg or text, target)

    # Não conseguiu parsear → retorna None
    msg = text
    for kw in REMINDER_KEYWORDS:
        msg = msg.replace(kw, "").strip()
    return (msg or text, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Brain — Lógica principal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

router = LLMRouter()
_reminder_chat_id = None  # Salva o chat_id pra enviar lembretes
_cot_enabled = False  # Chain of Thought toggle
_reflect_enabled = False  # Auto-reflexão toggle


async def build_system_prompt() -> str:
    """Monta o system prompt com identidade + core memory + contexto temporal."""
    identity = core.load_identity()
    core_mem = await core.get_core_memory_text()
    episodes = await core.get_recent_episodes(limit=3)

    # Contexto temporal
    now = datetime.now()
    time_ctx = now.strftime("Hoje é %A, %d/%m/%Y. São %H:%M (horário de Brasília).")
    days_pt = {
        "Monday": "segunda-feira", "Tuesday": "terça-feira",
        "Wednesday": "quarta-feira", "Thursday": "quinta-feira",
        "Friday": "sexta-feira", "Saturday": "sábado", "Sunday": "domingo",
    }
    for en, pt in days_pt.items():
        time_ctx = time_ctx.replace(en, pt)

    episode_text = ""
    if episodes:
        episode_text = "\n\n## Conversas recentes:\n"
        for ep in episodes:
            episode_text += f"- {ep['summary']}\n"

    # Reflexões ativas
    reflections = await core.get_active_reflections()
    reflection_text = ""
    if reflections:
        reflection_text = "\n\n## Lições aprendidas (auto-reflexão):\n"
        for r in reflections:
            reflection_text += f"- {r}\n"

    return f"""{identity}

---

## Contexto:
{time_ctx}

## Memória Core (fatos permanentes sobre o Criador):
{core_mem}
{episode_text}
{reflection_text}"""


async def execute_tools(text: str) -> tuple[str, str, str | None]:
    """Classifica a intenção e executa a tool correspondente, retornando o contexto. Retorna (tool_context, intent, query)."""
    intent, query = await classify_intent(text, router)
    logger.info(f"🎯 Intent: {intent} | Query: {query}")

    tool_context = ""

    if intent == "search" and query:
        logger.info(f"🔍 Buscando (deep): {query}")
        search_results = await web_search.web_search_deep(query)
        tool_context = f"\n\n## Resultados da busca web (use esses dados para responder com precisão):\n{search_results}"

    elif intent == "save_memory" and query:
        await core.save_core_fact("fato", query)
        logger.info(f"💾 Memória salva: {query}")
        tool_context = f"\n\n## [AÇÃO EXECUTADA] Fato salvo na memória permanente: '{query}'. Confirme brevemente."

    elif intent == "recall_memory":
        core_facts = await core.get_core_memory()
        if core_facts:
            facts_text = "\n".join([f"- [{f['category']}] {f['content']}" for f in core_facts])
            tool_context = f"\n\n## Tudo que sei sobre o Criador:\n{facts_text}"
        else:
            tool_context = "\n\n## Ainda não tenho fatos permanentes salvos."

    elif intent == "weather":
        weather_data = await core.get_weather()
        logger.info("🌤️ Clima consultado")
        tool_context = f"\n\n## Dados do clima (Open-Meteo):\n{weather_data}"

    elif intent == "status":
        status_data = await core.get_system_status()
        logger.info("📱 Status do sistema consultado")
        tool_context = f"\n\n## Status do dispositivo:\n{status_data}"

    elif intent == "flashlight":
        is_on = query == "on"
        result = await core.turn_on_flashlight(on=is_on)
        logger.info(f"🔦 Controle de lanterna executado: {result}")
        tool_context = f"\n\n## [AÇÃO FÍSICA EXECUTADA]\n{result}"

    elif intent == "location":
        result = await core.get_location()
        logger.info(f"📍 GPS consultado: {result}")
        tool_context = f"\n\n## [AÇÃO FÍSICA EXECUTADA]\nSensoriamento de localização concluído:\n{result}"

    elif intent == "url_read" and query:
        logger.info(f"🔗 Lendo URL: {query}")
        content = await web_search.web_read(query)
        tool_context = f"\n\n## Conteúdo da URL {query}:\n{content}"

    elif intent == "reminder" and query:
        msg, trigger = parse_reminder_time(query)
        if trigger:
            rid = await core.save_reminder(msg, trigger)
            time_str = trigger.strftime("%H:%M")
            logger.info(f"⏰ Reminder #{rid} agendado para {time_str}: {msg}")
            tool_context = f"\n\n## [AÇÃO EXECUTADA] Lembrete agendado para {time_str}: '{msg}'. Confirme brevemente."
        else:
            tool_context = "\n\n## Não entendi o horário do lembrete. Peça ao Criador pra esclarecer (ex: 'daqui a 10 minutos' ou 'às 18:00')."
            
    elif intent == "swarm" and query:
        logger.info(f"🐝 Enviando task para o Swarm Orchestrator: {query[:50]}")
        
        # Determinar a role dinamicamente (Mock rápido, ideal usar LLM pra classificar a melhor role)
        # Vamos assumir que se tem "revisa" ou "código", é revisor. Senão, pesquisador.
        role_to_use = "revisor" if any(w in query.lower() for w in ["revisa", "código", "codigo", "bug"]) else "pesquisador"
        
        # Função de callback pra quando o swarm terminar
        async def swarm_callback(result_text):
            if _reminder_chat_id:
                final_msg = f"🐝 **Retorno do Swarm ({role_to_use}):**\n\n{result_text}"
                await telegram_bot.send_simple_message(_reminder_chat_id, final_msg[:4000])
                
        # Submete à fila do orquestrador (não bloqueia a Iara)
        await orchestrator.submit_task(role_to_use, query, callback=swarm_callback)
        
        tool_context = f"\n\n## [AÇÃO EXECUTADA] A tarefa '{query}' foi delegada para a fila do Swarm com a persona '{role_to_use}'. Diga ao criador que a equipe está trabalhando nisso em background e avisará quando terminar."

    return tool_context, intent, query

async def process_message(text: str, message):
    """
    Pipeline principal:
    1. Comandos especiais → 2. Salva mensagem → 3. Classifica intent
    4. Executa tool → 5. Chama LLM → 6. Auto-detect → 7. Compacta
    """
    global _reminder_chat_id, _cot_enabled, _reflect_enabled
    chat_id = message.chat.id
    _reminder_chat_id = chat_id

    # 0. Comandos especiais (não salvam na memória)
    text_lower = text.strip().lower()
    if text_lower in ("/think on", "/think", "think on"):
        _cot_enabled = True
        await telegram_bot.send_simple_message(chat_id, "🧠 **Chain of Thought ativado.** Vou mostrar meu raciocínio antes de responder.")
        return
    elif text_lower in ("/think off", "think off"):
        _cot_enabled = False
        await telegram_bot.send_simple_message(chat_id, "💬 **Chain of Thought desativado.** Respostas diretas.")
        return
    elif text_lower in ("/reflect on", "/reflect", "reflect on"):
        _reflect_enabled = True
        await telegram_bot.send_simple_message(chat_id, "🔍 **Auto-reflexão ativada.** Vou avaliar minhas respostas silenciosamente.")
        return
    elif text_lower in ("/reflect off", "reflect off"):
        _reflect_enabled = False
        await telegram_bot.send_simple_message(chat_id, "🔍 **Auto-reflexão desativada.**")
        return

    # Comandos /worker
    elif text_lower.startswith("/worker"):
        parts = text.strip().split()
        if len(parts) >= 4 and parts[1].lower() == "add":
            name = parts[2]
            host = parts[3]
            skills = parts[4].split(",") if len(parts) > 4 else None
            worker_protocol.register_worker(name, host, skills)
            await telegram_bot.send_simple_message(chat_id, f"🐝 Worker **{name}** registrado ({host})")
        elif len(parts) >= 3 and parts[1].lower() == "remove":
            name = parts[2]
            worker_protocol.remove_worker(name)
            await telegram_bot.send_simple_message(chat_id, f"🐝 Worker **{name}** removido.")
        elif len(parts) >= 2 and parts[1].lower() in ("list", "ls", "status"):
            status = worker_protocol.list_all_workers()
            await telegram_bot.send_simple_message(chat_id, status)
        elif len(parts) >= 2 and parts[1].lower() == "ping":
            await telegram_bot.send_simple_message(chat_id, "🐝 Verificando workers...")
            await worker_protocol.health_check()
            status = worker_protocol.list_all_workers()
            await telegram_bot.send_simple_message(chat_id, status)
        else:
            await telegram_bot.send_simple_message(chat_id, (
                "🐝 **Comandos Worker:**\n"
                "`/worker add nome host [skills]`\n"
                "`/worker remove nome`\n"
                "`/worker list`\n"
                "`/worker ping`"
            ))
        return

    # Comando Manual pra testar consolidação
    elif text_lower == "/consolidate":
        await telegram_bot.send_simple_message(chat_id, "🧠 Iniciando consolidação de memória manual...")
        asyncio.create_task(_run_consolidation(chat_id))
        return

    # 0.5 Interceptar documentos anexados
    if text.startswith("📄FILE:"):
        parts = text[len("📄FILE:"):].split("|", 1)
        file_path = parts[0]
        question = parts[1] if len(parts) > 1 else None
        logger.info(f"📄 Analisando documento: {file_path}")
        await telegram_bot.send_simple_message(chat_id, "📄 **Analisando documento...**")
        result = await doc_reader.analyze_document(file_path, router, question)
        await telegram_bot.send_simple_message(chat_id, result)
        await core.save_message("assistant", result)
        return

    # 1. Salvar mensagem do Criador
    await core.save_message("user", text)

    # 1.5 Verificar se há plano de pesquisa pendente de aprovação
    pending = deep_research.get_pending_plan(chat_id)
    if pending:
        approval_words = ["ok", "sim", "vai", "pode", "aprova", "aprovar", "manda", "go", "yes", "bora", "faz", "inicia", "iniciar"]
        if any(w == text_lower or text_lower.startswith(w) for w in approval_words):
            # Aprovado! Executar plano
            deep_research.clear_pending_plan(chat_id)
            topic = pending["topic"]
            plan = pending["plan"]

            await telegram_bot.send_simple_message(chat_id, "🔬 **Pesquisa iniciada!** Acompanhe o progresso abaixo...")

            # Callback de progresso — envia updates pro Telegram
            async def progress_cb(msg: str):
                await telegram_bot.send_simple_message(chat_id, msg)

            # Executar plano com progresso
            all_data, sources = await deep_research.execute_plan(topic, plan, router, progress_cb)
            await progress_cb(f"📝 Sintetizando relatório com {len(sources)} fontes...")
            report = await deep_research.synthesize_with_citations(topic, all_data, sources, router)

            await telegram_bot.send_simple_message(chat_id, report)
            await core.save_message("assistant", report)
            return
        else:
            # Usuário editou o plano — cancelar e tratar como mensagem normal
            deep_research.clear_pending_plan(chat_id)
            logger.info("📋 Plano de pesquisa cancelado/editado pelo Criador")

    # 2. Classificar intent e Executar tool se necessário
    tool_context, intent, query = await execute_tools(text)

    if intent == "deep_research" and query:
        logger.info(f"🔬 Deep Research Plan & Execute: {query}")
        await telegram_bot.send_simple_message(chat_id, "🔬 **Analisando tema e criando plano de pesquisa...**")
        
        # Fase 1: Criar plano
        plan = await deep_research.create_plan(query, router)
        plan_msg = deep_research.format_plan_message(query, plan)
        
        # Fase 2: Mostrar plano e aguardar aprovação
        deep_research.save_pending_plan(chat_id, query, plan)
        await telegram_bot.send_simple_message(chat_id, plan_msg)
        await core.save_message("assistant", plan_msg)
        return  # Aguarda resposta do usuário

    # 4. Montar contexto e streaming
    system_prompt = await build_system_prompt()

    # Injetar CoT se ativado
    cot_instruction = ""
    if _cot_enabled:
        cot_instruction = (
            "\n\n## Modo Chain of Thought ATIVADO\n"
            "Antes de responder, raciocine passo-a-passo dentro de tags <think>...</think>.\n"
            "Depois da tag </think>, dê a resposta final normalmente.\n"
            "Exemplo:\n"
            "<think>O Criador perguntou X. Preciso considerar Y e Z...</think>\n"
            "Resposta final aqui."
        )

    conversation = await core.get_conversation()
    messages = [
        {"role": "system", "content": system_prompt + tool_context + cot_instruction},
        *conversation,
    ]

    stream = router.generate_stream(messages)
    full_response = await telegram_bot.send_streaming_response(
        chat_id, stream, reply_to=message.message_id
    )

    # 5. Processar CoT — extrair e enviar raciocínio separado
    if full_response and _cot_enabled:
        think_match = re.search(r'<think>(.*?)</think>', full_response, re.DOTALL)
        if think_match:
            thinking = think_match.group(1).strip()
            # Enviar o raciocínio como mensagem separada
            if thinking:
                await telegram_bot.send_simple_message(chat_id, f"🧠 *Raciocínio:*\n{thinking}")
            # Limpar a resposta final
            clean_response = re.sub(r'<think>.*?</think>\s*', '', full_response, flags=re.DOTALL).strip()
            if clean_response != full_response:
                full_response = clean_response

    # 6. Salvar resposta
    if full_response:
        await core.save_message("assistant", full_response)

    # 7. Auto-detect fatos
    if full_response and intent == "chat":
        asyncio.create_task(_auto_detect_memory(text, router))

    # 8. Auto-reflexão silenciosa
    if full_response and _reflect_enabled:
        asyncio.create_task(_auto_reflect(text, full_response, router))

    # 7. Compactação
    count = await core.get_working_memory_count()
    if count > config.MAX_WORKING_MEMORY:
        logger.info(f"📦 Compactando working memory ({count} msgs)...")
        summary_messages = [
            {"role": "system", "content": "Resuma em 2-3 frases:"},
            *conversation,
        ]
        summary = await router.generate(summary_messages)
        if isinstance(summary, str):
            await core.compact_working_memory(summary)


async def _auto_detect_memory(user_text: str, router: LLMRouter):
    """Detecta fatos pessoais na mensagem do Criador (background)."""
    try:
        result = await router.generate([
            {"role": "system", "content": (
                "Analise a mensagem. Se contém um FATO PESSOAL importante "
                "(preferência, hobby, nome, profissão, projeto), "
                "extraia em uma frase curta. Se NÃO, responda: NENHUM\n"
                "Exemplos: 'Eu moro em SP' → 'Mora em São Paulo' | 'oi' → NENHUM"
            )},
            {"role": "user", "content": user_text},
        ], temperature=0.0)

        if isinstance(result, str) and "NENHUM" not in result.upper():
            fact = result.strip().strip('"').strip("'")
            if 5 < len(fact) < 200:
                await core.save_core_fact("auto", fact)
                logger.info(f"🧠 Auto-memorizado: {fact}")
    except Exception as e:
        logger.debug(f"Auto-detect falhou (ok): {e}")


async def _auto_reflect(user_text: str, response: str, router: LLMRouter):
    """Avalia a qualidade da própria resposta (background, silencioso)."""
    try:
        result = await router.generate([
            {"role": "system", "content": (
                "Avalie esta resposta de IA a uma mensagem do usuário.\n"
                "Critérios:\n"
                "1. Respondeu o que foi perguntado?\n"
                "2. Foi concisa ou enrolou?\n"
                "3. Inventou algum dado?\n"
                "4. O tom foi natural?\n\n"
                "Se tudo OK, responda: OK\n"
                "Se encontrou problema, responda com UMA lição curta de melhoria "
                "(máx 1 frase). Exemplo: 'Ser mais direta em perguntas simples'\n"
                "NÃO inclua explicações, só a lição."
            )},
            {"role": "user", "content": f"Pergunta: {user_text}\n\nResposta: {response[:500]}"},
        ], temperature=0.0)

        if isinstance(result, str) and "OK" not in result.upper().strip():
            lesson = result.strip().strip('"').strip("'")
            if 5 < len(lesson) < 150:
                await core.save_reflection(lesson)
                logger.info(f"🔍 Auto-reflexão: {lesson}")
    except Exception as e:
        logger.debug(f"Auto-reflect falhou (ok): {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Reminder Loop — Verifica lembretes pendentes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _reminder_loop():
    """Verifica lembretes pendentes a cada 30 segundos."""
    await asyncio.sleep(10)  # espera bot iniciar
    logger.info("⏰ Reminder loop iniciado")
    while True:
        try:
            pending = await core.get_pending_reminders()
            for r in pending:
                if _reminder_chat_id:
                    msg = f"⏰ **Lembrete:** {r['message']}"
                    await telegram_bot.send_simple_message(_reminder_chat_id, msg)
                    await core.mark_reminder_sent(r["id"])
                    logger.info(f"⏰ Lembrete #{r['id']} enviado: {r['message']}")
        except Exception as e:
            logger.debug(f"Reminder loop erro: {e}")

        await asyncio.sleep(30)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Preference Learning & Proactive Alerts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_last_preference_check_count = 0
_last_battery_alert = None
_last_weather_alert = None


async def _proactive_alerts_loop():
    """Monitora a saúde do sistema e do hardware. Alerta via Telegram se houver problema."""
    global _reminder_chat_id, _last_battery_alert, _last_weather_alert
    await asyncio.sleep(20) # Começa as checagens 20s após iniciar
    logger.info("🛡️ Proactive alerts loop iniciado (Monitoramento de Bateria)")

    while True:
        try:
            if _reminder_chat_id: # Só alerta se tivermos um chat registrado
                status_data = await core.get_system_status()
                # Procurar por sinais de bateria fraca nas strings de status
                # status_data retorna algo como "IARA (Master):\n  Bateria: 85% ..."
                
                # Vamos simplificar pegando as porcentagens
                import re
                bateria_matches = re.finditer(r'Bateria:\s*(\d+)%', status_data)
                
                for match in bateria_matches:
                    nivel = int(match.group(1))
                    
                    # Limiar provisório de 15%
                    if nivel <= 15:
                        agora = datetime.now()
                        # Não ficar enviando toda hora, alertar a cada 3 horas
                        if not _last_battery_alert or (agora - _last_battery_alert).total_seconds() > (3 * 3600):
                            await telegram_bot.send_simple_message(
                                _reminder_chat_id, 
                                f"⚠️ **Alerta Proativo de Bateria:**\n"
                                f"Detectei um nível crítico de energia ({nivel}%).\nPor favor, conecte o carregador."
                            )
                            _last_battery_alert = agora
                            logger.warning(f"🔋 Alerta de bateria enviado (Nível: {nivel}%)")

                # ==========================================
                # Alertas Proativos de Clima (Chuva Iminente)
                # ==========================================
                weather_data = await core.get_weather()
                if "Chuva" in weather_data or "Pancadas" in weather_data or "Temporal" in weather_data:
                    agora = datetime.now()
                    # Enviar alerta de chuva no máximo a cada 6 horas
                    if not _last_weather_alert or (agora - _last_weather_alert).total_seconds() > (6 * 3600):
                        await telegram_bot.send_simple_message(
                            _reminder_chat_id, 
                            f"🌧️ **Alerta Proativo de Clima:**\n"
                            f"Há previsão de chuva para hoje!\nDetalhes: {weather_data}"
                        )
                        _last_weather_alert = agora
                        logger.warning(f"🌧️ Alerta de chuva enviado!")

        except Exception as e:
            logger.debug(f"Erro no alerts loop: {e}")

        # Checa a cada 15 minutos (900s) para não floodar as APIs
        await asyncio.sleep(900)




async def _preference_learning_loop():
    """
    A cada 30 min verifica se acumulou 10+ episódios novos.
    Se sim, analisa padrões recorrentes e salva na core memory.
    Versão conservadora: só salva padrões com 3+ ocorrências.
    """
    global _last_preference_check_count
    await asyncio.sleep(60)  # espera bot estabilizar
    logger.info("🧠 Preference learning loop iniciado")

    while True:
        try:
            current_count = await core.get_episode_count()

            # Só analisa se acumulou 10+ episódios novos
            if current_count - _last_preference_check_count >= 10:
                logger.info(f"🧠 Analisando preferências ({current_count} episódios)...")

                # Pegar todos os episódios recentes
                episodes = await core.get_all_episodes(limit=20)
                existing_facts = await core.get_core_memory_text()

                if episodes:
                    episodes_text = "\n".join([f"- {ep}" for ep in episodes])

                    result = await router.generate([
                        {"role": "system", "content": (
                            "Analise esses resumos de conversas e extraia PADRÕES RECORRENTES sobre o usuário. "
                            "REGRAS ESTRITAS:\n"
                            "1. Só extraia padrões que aparecem 3+ vezes nos resumos\n"
                            "2. Ignore tópicos que apareceram apenas uma vez\n"
                            "3. Foque em: interesses, hábitos, horários, preferências, projetos\n"
                            "4. Formato: uma preferência por linha, curta e factual\n"
                            "5. Se não há padrões claros, responda APENAS: NENHUM\n\n"
                            f"Fatos que JÁ EXISTEM na memória (NÃO repita esses):\n{existing_facts}\n\n"
                            f"Resumos das últimas conversas:\n{episodes_text}"
                        )},
                    ], temperature=0.0)

                    if isinstance(result, str) and "NENHUM" not in result.upper():
                        # Parsear cada linha como uma preferência
                        new_prefs = [
                            line.strip().lstrip("-•").strip()
                            for line in result.strip().split("\n")
                            if line.strip() and len(line.strip()) > 5 and len(line.strip()) < 200
                        ]

                        saved = 0
                        for pref in new_prefs[:5]:  # Máximo 5 por batch
                            # Verificar se não é duplicata
                            if pref.lower() not in existing_facts.lower():
                                await core.save_core_fact("preferência", pref)
                                saved += 1

                        if saved > 0:
                            logger.info(f"🧠 {saved} preferências aprendidas!")

                _last_preference_check_count = current_count

        except Exception as e:
            logger.debug(f"Preference learning erro: {e}")

        await asyncio.sleep(1800)  # 30 minutos


async def _heartbeat_and_compaction_loop():
    """Executa heartbeat e compactação da memória de trabalho a cada 10 minutos."""
    await asyncio.sleep(60) # Espera inicial
    logger.info("🗑️ Heartbeat + Compaction loop iniciado")
    while True:
        try:
            logger.info("🗑️ Executando Heartbeat + Compaction das memórias...")
            await core.compact_working_memory(router) # Assuming 'router' is accessible or passed
        except Exception as e:
            logger.debug(f"Erro no heartbeat: {e}")

        await asyncio.sleep(600)  # roda a cada 10 min

async def _worker_health_loop():
    """Ping contínuo nos workers registrados para saber quem está online."""
    await asyncio.sleep(10)  # Espera inicial
    logger.info("🐝 Worker Health Loop iniciado")
    while True:
        try:
            await worker_protocol.health_check()
        except Exception as e:
            logger.debug(f"Erro no health check dos workers: {e}")
        
        await asyncio.sleep(60) # Checa a cada 1 minuto

async def _run_consolidation(chat_id=None):
    """Lógica pesada de consolidação."""
    logger.info("🌌 Iniciando Nightly Memory Consolidation...")
    if chat_id:
        await telegram_bot.send_simple_message(chat_id, "🌌 Consolidando episódios antigos...")
        
    episodes = await core.get_unprocessed_episodes(limit=30)
    if not episodes:
        logger.info("🌌 Sem episódios antigos para consolidar.")
        if chat_id: await telegram_bot.send_simple_message(chat_id, "Nenhum episódio pra consolidar.")
        return
        
    ep_text = "\n".join([f"[{e['timestamp']}] {e['summary']}" for e in episodes])
    existing_core = await core.get_core_memory_text()
    
    prompt = f"""Você é o subsistema de consolidação de memórias da IARA.
Seu trabalho é ler um lote de resumos antigos de conversas e extrair FATOS PERMANENTES sobre o usuário ou sobre a própria Iara que devem ser lembrados para sempre.

Regras:
1. Extraia apenas fatos importantes (preferências, medos, rotinas, dados fixos). Ignore conversas triviais.
2. Cada fato deve ser uma frase curta e direta (ex: "O usuário odeia pizza de abacaxi").
3. Não repita fatos que já estão na Core Memory atual.
4. Responda APENAS com a lista de novos fatos, um por linha, começando com '- '. Se não houver nada útil, responda 'NADA'.

Core Memory Atual:
{existing_core}

Lote de Episódios:
{ep_text}
"""
    result = await router.generate([{"role": "user", "content": prompt}], temperature=0.1)
    
    facts_saved = 0
    if isinstance(result, str) and "NADA" not in result.upper():
        lines = [line.lstrip("- ").strip() for line in result.split("\n") if line.strip().startswith("-")]
        for fact in lines:
            if fact:
                await core.save_core_fact("consolidado", fact)
                facts_saved += 1
                
    # Deleta os episódios já processados pra não crescer infinito
    ids_to_del = [e["id"] for e in episodes]
    await core.delete_old_episodes(ids_to_del)
    
    msg = f"🌌 Consolidação concluída! {len(episodes)} episódios apagados. {facts_saved} novos fatos permanentes aprendidos."
    logger.info(msg)
    if chat_id: await telegram_bot.send_simple_message(chat_id, msg)

async def _memory_consolidation_loop():
    """Roda todo dia de madrugada (03:00) para processar os episódios e limpar o DB."""
    await asyncio.sleep(120)  # Espera inicial
    logger.info("🌌 Nightly Memory Consolidation Loop iniciado")
    while True:
        try:
            now = datetime.now()
            # Roda entre as 03:00 e 04:00 da manhã
            if now.hour == 3:
                await _run_consolidation()
                # Dorme 2 horas pra garantir que não vai processar de novo hoje
                await asyncio.sleep(7200)
                continue
        except Exception as e:
            logger.error(f"Erro na consolidação de memórias: {e}")
            
        await asyncio.sleep(3600)  # Checa a cada hora se deu a hora

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Inicialização
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def main():
    """Inicializa tudo e inicia o bot."""
    logger.info("🌊 Iara está acordando...")

    await core.init_db()
    logger.info("✅ Memória inicializada")
    
    # Recuperar jobs do swarm que podem ter sido interrompidos
    await orchestrator.load_pending_jobs()

    status = router.get_status()
    logger.info(f"🧠 LLMs ativos: {status['providers_ativos']}")

    telegram_bot.set_message_handler(process_message)
    logger.info("✅ Telegram configurado")

    # Iniciar loops em background
    asyncio.create_task(_reminder_loop())
    asyncio.create_task(_preference_learning_loop())
    asyncio.create_task(_proactive_alerts_loop())
    asyncio.create_task(_worker_health_loop())
    asyncio.create_task(_heartbeat_and_compaction_loop())
    asyncio.create_task(_memory_consolidation_loop())

    # Iniciar Dashboard Web
    logger.info("🌐 Iniciando Dashboard Web (FastAPI) na porta 8080...")
    threading.Thread(target=dashboard_api.run_dashboard, daemon=True).start()

    logger.info("🌊 Iara está online! Esperando mensagens...")
    await telegram_bot.start_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🌊 Iara dormindo... Até logo!")
        sys.exit(0)

--- END FILE ---

--- FILE: core.py ---
"""
core.py — Memória em 3 camadas (Working, Episodic, Core)
Gerencia toda a persistência de estado da Kitty via SQLite.
"""

import aiosqlite
import json
import logging
from datetime import datetime

import config

logger = logging.getLogger("core")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Inicialização do banco de dados
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def init_db():
    """Cria as 3 tabelas de memória se não existirem."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        # Working Memory — conversas ativas (curto prazo)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS working_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Episodic Memory — resumos de conversas passadas (médio prazo)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary TEXT NOT NULL,
                tags TEXT DEFAULT '',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Core Memory — fatos permanentes sobre o usuário (longo prazo)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS core_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Swarm Jobs (Persistência da fila do Orquestrador contra Crash/Amnésia)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS swarm_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()
        logger.info("✅ Banco de dados inicializado com 4 tabelas centrais.")

    # Criar tabela de lembretes separadamente (migration segura)
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                trigger_time DATETIME NOT NULL,
                sent BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de auto-reflexões
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Working Memory — Conversa atual (RAM da Kitty)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_message(role: str, content: str):
    """Salva uma mensagem na working memory."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute(
            "INSERT INTO working_memory (role, content) VALUES (?, ?)",
            (role, content)
        )
        await db.commit()


async def get_conversation(limit: int = None) -> list[dict]:
    """
    Retorna o histórico de conversas recente.
    Se limit for None, usa MAX_WORKING_MEMORY do config.
    """
    if limit is None:
        limit = config.MAX_WORKING_MEMORY

    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT role, content FROM working_memory ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()

    # Retorna em ordem cronológica (mais antigo primeiro)
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


async def get_working_memory_count() -> int:
    """Conta quantas mensagens tem na working memory."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM working_memory")
        row = await cursor.fetchone()
    return row[0]


async def compact_working_memory(summary: str):
    """
    Compacta working memory:
    1. Salva um resumo na episodic memory
    2. Limpa a working memory (mantém últimas 4 mensagens)
    """
    # Salvar resumo na episodic
    await save_episode(summary)

    # Manter apenas as últimas 4 mensagens
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute("""
            DELETE FROM working_memory WHERE id NOT IN (
                SELECT id FROM working_memory ORDER BY id DESC LIMIT 4
            )
        """)
        await db.commit()

    logger.info("📦 Working memory compactada. Resumo salvo na episodic.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Episodic Memory — Conversas passadas (HD da Kitty)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_episode(summary: str, tags: str = ""):
    """Salva um resumo de conversa na episodic memory."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute(
            "INSERT INTO episodic_memory (summary, tags) VALUES (?, ?)",
            (summary, tags)
        )
        await db.commit()


async def get_episode_count() -> int:
    """Conta quantos episódios existem."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM episodic_memory")
        row = await cursor.fetchone()
    return row[0]


async def get_all_episodes(limit: int = 20) -> list[str]:
    """Retorna os resumos mais recentes como lista de strings."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT summary FROM episodic_memory ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
    return [r[0] for r in reversed(rows)]


async def get_recent_episodes(limit: int = 5) -> list[dict]:
    """Retorna os episódios mais recentes."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT summary, tags, timestamp FROM episodic_memory ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()

    return [
        {"summary": r[0], "tags": r[1], "timestamp": r[2]}
        for r in reversed(rows)
    ]


async def search_episodes(query: str, limit: int = 3) -> list[dict]:
    """Busca episódios por palavra-chave (busca simples em texto)."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT summary, tags, timestamp FROM episodic_memory WHERE summary LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit)
        )
        rows = await cursor.fetchall()

    return [
        {"summary": r[0], "tags": r[1], "timestamp": r[2]}
        for r in rows
    ]

async def get_unprocessed_episodes(limit: int = 50) -> list[dict]:
    """Retorna os episódios mais antigos para consolidação na core memory."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT id, summary, timestamp FROM episodic_memory ORDER BY id ASC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        
    return [
        {"id": r[0], "summary": r[1], "timestamp": r[2]}
        for r in rows
    ]

async def delete_old_episodes(ids: list[int]):
    """Remove episódios após a consolidação."""
    if not ids: return
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        # Usa placeholdering pro IN clause
        placeholders = ",".join("?" * len(ids))
        await db.execute(f"DELETE FROM episodic_memory WHERE id IN ({placeholders})", ids)
        await db.commit()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Core Memory — Fatos permanentes (Alma da Kitty)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_core_fact(category: str, content: str, confidence: float = 1.0):
    """
    Salva um fato permanente na core memory.
    Se o fato já existir (mesmo conteúdo), atualiza a confiança.
    """
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        # Verifica se já existe
        cursor = await db.execute(
            "SELECT id FROM core_memory WHERE content = ?", (content,)
        )
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                "UPDATE core_memory SET confidence = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (confidence, existing[0])
            )
        else:
            await db.execute(
                "INSERT INTO core_memory (category, content, confidence) VALUES (?, ?, ?)",
                (category, content, confidence)
            )

        await db.commit()


async def get_core_memory() -> list[dict]:
    """Retorna todos os fatos da core memory, ordenados por confiança."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT category, content, confidence, updated_at FROM core_memory ORDER BY confidence DESC"
        )
        rows = await cursor.fetchall()

    return [
        {
            "category": r[0],
            "content": r[1],
            "confidence": r[2],
            "updated_at": r[3],
        }
        for r in rows
    ]


async def get_core_memory_text() -> str:
    """Retorna a core memory formatada como texto para injetar no prompt."""
    facts = await get_core_memory()
    if not facts:
        return "Ainda não conheço fatos permanentes sobre o Criador."

    lines = []
    for f in facts:
        lines.append(f"- [{f['category']}] {f['content']}")

    return "\n".join(lines)


async def delete_core_fact(content: str):
    """Remove um fato da core memory."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute(
            "DELETE FROM core_memory WHERE content = ?", (content,)
        )
        await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Reminders — Lembretes agendados
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_reminder(message: str, trigger_time: datetime) -> int:
    """Salva um lembrete e retorna o ID."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (message, trigger_time) VALUES (?, ?)",
            (message, trigger_time.isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_reminders() -> list[dict]:
    """Retorna lembretes pendentes que já passaram do horário."""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT id, message, trigger_time FROM reminders WHERE sent = 0 AND trigger_time <= ?",
            (now,)
        )
        rows = await cursor.fetchall()

    return [{"id": r[0], "message": r[1], "trigger_time": r[2]} for r in rows]


async def mark_reminder_sent(reminder_id: int):
    """Marca um lembrete como enviado."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute(
            "UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,)
        )
        await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Auto-Reflexão — Lições aprendidas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_reflection(lesson: str):
    """Salva uma lição de auto-reflexão."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute(
            "INSERT INTO reflections (lesson) VALUES (?)", (lesson,)
        )
        # Manter apenas as 5 mais recentes
        await db.execute("""
            DELETE FROM reflections WHERE id NOT IN (
                SELECT id FROM reflections ORDER BY id DESC LIMIT 5
            )
        """)
        await db.commit()


async def get_active_reflections() -> list[str]:
    """Retorna as 5 reflexões mais recentes."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "SELECT lesson FROM reflections ORDER BY id DESC LIMIT 5"
        )
        rows = await cursor.fetchall()
    return [r[0] for r in reversed(rows)]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Weather — Clima via Open-Meteo (grátis, sem API key)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_weather(lat: float = -23.55, lon: float = -46.63) -> str:
    """
    Busca clima atual via Open-Meteo API.
    Default: São Paulo (pode ser alterado via core memory).
    """
    import aiohttp
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            f"&timezone=America/Sao_Paulo"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return "Não consegui acessar os dados de clima."
                data = await resp.json()

        current = data.get("current", {})
        temp = current.get("temperature_2m", "?")
        humidity = current.get("relative_humidity_2m", "?")
        wind = current.get("wind_speed_10m", "?")
        code = current.get("weather_code", 0)

        # Traduzir weather code
        weather_desc = _weather_code_to_text(code)

        return (
            f"Clima atual:\n"
            f"- Temperatura: {temp}°C\n"
            f"- Umidade: {humidity}%\n"
            f"- Vento: {wind} km/h\n"
            f"- Condição: {weather_desc}"
        )
    except Exception as e:
        return f"Erro ao buscar clima: {e}"


def _weather_code_to_text(code: int) -> str:
    """Traduz WMO weather code para texto."""
    codes = {
        0: "Céu limpo", 1: "Praticamente limpo", 2: "Parcialmente nublado",
        3: "Nublado", 45: "Nevoeiro", 48: "Nevoeiro com geada",
        51: "Garoa leve", 53: "Garoa moderada", 55: "Garoa forte",
        61: "Chuva leve", 63: "Chuva moderada", 65: "Chuva forte",
        71: "Neve leve", 73: "Neve moderada", 75: "Neve forte",
        80: "Pancadas leves", 81: "Pancadas moderadas", 82: "Pancadas fortes",
        95: "Tempestade", 96: "Tempestade com granizo leve", 99: "Tempestade com granizo",
    }
    return codes.get(code, f"Código {code}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# System Status — Info do dispositivo (Termux)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_system_status() -> str:
    """Retorna status do sistema via Termux API."""
    import subprocess
    import json as json_mod
    parts = []

    # Bateria
    try:
        res = subprocess.run(
            ["termux-battery-status"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            bat = json_mod.loads(res.stdout)
            parts.append(f"Bateria: {bat.get('percentage', '?')}% ({bat.get('status', '?')})")
    except Exception:
        parts.append("Bateria: indisponível (sem Termux API)")

    # Storage
    try:
        res = subprocess.run(
            ["df", "-h", "/data"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            lines = res.stdout.strip().split("\n")
            if len(lines) > 1:
                cols = lines[1].split()
                parts.append(f"Storage: {cols[2]} usado / {cols[1]} total ({cols[4]} ocupado)")
    except Exception:
        parts.append("Storage: indisponível")

    # Uptime
    try:
        res = subprocess.run(
            ["uptime", "-p"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            parts.append(f"Uptime: {res.stdout.strip()}")
    except Exception:
        pass

    # RAM
    try:
        res = subprocess.run(
            ["free", "-m"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            lines = res.stdout.strip().split("\n")
            if len(lines) > 1:
                cols = lines[1].split()
                # Mem: total used free shared buffers cached
                parts.append(f"RAM: {cols[2]}MB usado / {cols[1]}MB total")
    except Exception:
        pass

    # CPU
    try:
        res = subprocess.run(
            ["top", "-n", "1", "-m", "1"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            for line in res.stdout.split("\n"):
                if line.startswith("User"):
                    parts.append(f"CPU: {line.strip()}")
                    break
    except Exception:
        pass

    return "\n  ".join(parts) if parts else "Status do sistema indisponível."


    return "\n  ".join(parts) if parts else "Status do sistema indisponível."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Hardware Control (Cyber-Mãos)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def turn_on_flashlight(on: bool = True) -> str:
    """Acende ou apaga a lanterna do dispositivo via termux-torch."""
    import subprocess
    cmd = "on" if on else "off"
    try:
        res = subprocess.run(
            ["termux-torch", cmd], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            return f"Lanterna {'ligada' if on else 'desligada'} com sucesso."
        return f"Falha ao controlar lanterna: {res.stderr}"
    except Exception as e:
        return f"Erro ao acessar termux-torch: {e}"


async def get_location() -> str:
    """Pega a localização atual do GPS."""
    import subprocess
    import json as json_mod
    try:
        res = subprocess.run(
            ["termux-location", "-p", "network", "-r", "once"], capture_output=True, text=True, timeout=10
        )
        if res.returncode == 0:
            loc = json_mod.loads(res.stdout)
            lat = loc.get("latitude", "?")
            lon = loc.get("longitude", "?")
            return f"Localização atual: Latitude {lat}, Longitude {lon} (https://maps.google.com/?q={lat},{lon})"
        return f"Falha ao obter localização: {res.stderr}"
    except Exception as e:
        return f"Erro ao acessar termux-location: {e}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# File I/O — Kitty Shadow (workspace de arquivos)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def write_to_shadow(filename: str, content: str) -> str:
    """Salva arquivo no Kitty_Shadow (pasta de trabalho)."""
    config.SHADOW_DIR.mkdir(exist_ok=True)
    filepath = config.SHADOW_DIR / filename
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


async def read_file(filename: str) -> str:
    """Lê arquivo do Kitty_Shadow."""
    filepath = config.SHADOW_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return f"Arquivo '{filename}' não encontrado."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Identity — Carrega SOUL/STYLE/SKILLS do disco
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_identity() -> str:
    """
    Carrega os arquivos de identidade (SOUL.md, STYLE.md, SKILLS.md)
    e os concatena para injeção no system prompt.
    """
    identity_parts = []

    for filename in ["SOUL.md", "STYLE.md", "SKILLS.md"]:
        filepath = config.IDENTITY_DIR / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            identity_parts.append(content)
        else:
            logger.warning(f"⚠️ Arquivo de identidade não encontrado: {filepath}")

    return "\n\n---\n\n".join(identity_parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gerenciamento de Fila Swarm (Anti-Crash)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_swarm_job(role_name: str, payload: str) -> int:
    """Insere um novo job pendente na fila do BD."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        cursor = await db.execute(
            "INSERT INTO swarm_jobs (role_name, payload) VALUES (?, ?)",
            (role_name, payload)
        )
        await db.commit()
        return cursor.lastrowid

async def get_pending_swarm_jobs() -> list[dict]:
    """Retorna todos os jobs pending ou processing (recuperação pós-crash)."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM swarm_jobs WHERE status IN ('pending', 'processing') ORDER BY created_at ASC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def update_swarm_job_status(job_id: int, status: str, result: str = None):
    """Atualiza o status (e resultado opcional) de um job no banco."""
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        if result is not None:
            await db.execute(
                "UPDATE swarm_jobs SET status = ?, result = ? WHERE id = ?",
                (status, result, job_id)
            )
        else:
            await db.execute(
                "UPDATE swarm_jobs SET status = ? WHERE id = ?",
                (status, job_id)
            )
        await db.commit()

--- END FILE ---

--- FILE: config.py ---
"""
config.py — Configurações centralizadas do KittyClaw/ZeroClaw
Todas as constantes, limites e paths ficam aqui.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Keys
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "__REDACTED__")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "__REDACTED__")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "__REDACTED__")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "__REDACTED__")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "__REDACTED__")
USER_ID_ALLOWED = int(os.getenv("USER_ID_ALLOWED", "0"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM Providers — configuração dos modelos e endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM_PROVIDERS = [
    {
        "name": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": GROQ_API_KEY,
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": True,
    },
    {
        "name": "kimi",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": NVIDIA_NIM_API_KEY,
        "model": "moonshotai/kimi-k2.5",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": False,
    },
    {
        "name": "cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key": CEREBRAS_API_KEY,
        "model": "llama3.1-8b",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": False,  # 8B model não é confiável com tools
    },
    {
        "name": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_API_KEY,
        "model": "deepseek/deepseek-r1",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_tools": False,  # R1 não suporta tools nativamente
    },
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Guardrails e Stop Conditions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_RETRIES_PER_TASK = 5         # Máximo de tentativas antes de pedir ajuda humana
LLM_TIMEOUT_SECONDS = 60        # Timeout por chamada de LLM
MAX_WORKING_MEMORY = 20         # Mensagens no working memory antes de compactar
MAX_TOOL_CALLS_PER_TURN = 5     # Máximo de tools executadas por turno

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Swarm Orchestrator (Load Balancing & Anti-OOM)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_WORKERS_S21FE = 3           # Prioridade 1: Aguenta mais carga isolada
MAX_WORKERS_ULTRA = 1           # Prioridade 2 (Overflow): Protegido pra não crashar o MMRPG

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Paths
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import pathlib

BASE_DIR = pathlib.Path(__file__).parent
DB_PATH = BASE_DIR / "kitty_memory.db"
IDENTITY_DIR = BASE_DIR / "identity"
SKILLS_DIR = BASE_DIR / "skills"
SHADOW_DIR = BASE_DIR / "Kitty_Shadow"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Web Search — limites diários para economizar cotas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JINA_API_URL = "https://r.jina.ai/"
DDG_MAX_RESULTS = 5
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "__REDACTED__")
BRAVE_MAX_DAILY = 60  # 2000/mês ÷ 30 dias

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Telegram
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STREAMING_EDIT_INTERVAL = 0.8  # Segundos entre edições da mensagem (streaming)

--- END FILE ---
