
--- FILE: telegram_bot.py ---
"""
telegram_bot.py — Interface Telegram da Iara
Toda a lógica de interação com o usuário via Telegram fica aqui.
"""

import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

import config

logger = logging.getLogger("telegram")

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Callback que será configurado pelo brain.py
_message_handler = None


def set_message_handler(handler):
    """Define a função que processa mensagens (configurada pelo brain.py)."""
    global _message_handler
    _message_handler = handler


def sanitize_markdown(text: str) -> str:
    """
    Sanitiza Markdown para Telegram.
    Telegram usa um subset limitado e crasha com marcadores desbalanceados.
    """
    # Bold **: deve ter pares
    count_bold = text.count("**")
    if count_bold % 2 != 0:
        text = text + "**"

    # Code blocks ```: devem ter pares
    count_code_block = text.count("```")
    if count_code_block % 2 != 0:
        text = text + "\n```"

    # Inline code `: deve ter pares (excluindo ```)
    temp = text.replace("```", "XXX")
    count_inline = temp.count("`")
    if count_inline % 2 != 0:
        text = text + "`"

    return text


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Resposta ao /start."""
    if message.from_user.id != config.USER_ID_ALLOWED:
        await message.answer("🚫 Acesso não autorizado.")
        return

    await message.answer(
        "🌊 Oi Criador! Iara online e pronta.\n"
        "Manda qualquer mensagem que eu respondo!",
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.message()
async def handle_message(message: types.Message):
    """Captura todas as mensagens e roteia para o brain."""
    if message.from_user.id != config.USER_ID_ALLOWED:
        return

    if not _message_handler:
        await message.answer("⚠️ Meu cérebro ainda não carregou. Tenta de novo em 5s.")
        return

    text = message.text or message.caption or ""

    # Detectar documento anexado
    file_path = None
    if message.document:
        try:
            import os
            file_info = await bot.get_file(message.document.file_id)
            file_name = message.document.file_name or "arquivo"
            file_path = f"/tmp/{file_name}"
            await bot.download_file(file_info.file_path, file_path)
            logger.info(f"📄 Arquivo baixado: {file_name}")
            text = f"📄FILE:{file_path}|{text}" if text else f"📄FILE:{file_path}|analisa este documento"
        except Exception as e:
            logger.error(f"Erro baixando arquivo: {e}")
            await message.answer(f"❌ Não consegui baixar o arquivo: {str(e)[:200]}")
            return

    if not text.strip():
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        await _message_handler(text, message)
    except Exception as e:
        logger.error(f"❌ Erro processando mensagem: {e}", exc_info=True)
        await message.answer(
            f"😿 Algo deu errado. Erro: {str(e)[:200]}\n"
            "Tenta de novo em alguns segundos.",
        )


async def send_streaming_response(chat_id: int, stream_generator, reply_to: int = None):
    """Envia resposta com streaming progressivo."""
    full_text = ""
    sent_message = None
    last_edit_length = 0
    edit_interval = config.STREAMING_EDIT_INTERVAL

    try:
        async for chunk in stream_generator:
            full_text += chunk

            if len(full_text) - last_edit_length < 40:
                continue

            display_text = full_text + " ▌"

            if sent_message is None:
                sent_message = await bot.send_message(
                    chat_id,
                    display_text,
                    reply_to_message_id=reply_to,
                )
            else:
                try:
                    await bot.edit_message_text(
                        display_text,
                        chat_id=chat_id,
                        message_id=sent_message.message_id,
                    )
                except Exception:
                    pass

            last_edit_length = len(full_text)
            await asyncio.sleep(edit_interval)

        # Mensagem final — sanitiza Markdown antes de enviar
        if sent_message and full_text:
            clean_text = sanitize_markdown(full_text)
            try:
                await bot.edit_message_text(
                    clean_text,
                    chat_id=chat_id,
                    message_id=sent_message.message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                # Markdown falhou mesmo sanitizado → texto puro
                try:
                    await bot.edit_message_text(
                        full_text,
                        chat_id=chat_id,
                        message_id=sent_message.message_id,
                    )
                except Exception:
                    pass
        elif full_text and not sent_message:
            clean_text = sanitize_markdown(full_text)
            try:
                await bot.send_message(
                    chat_id, clean_text,
                    reply_to_message_id=reply_to,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                await bot.send_message(
                    chat_id, full_text,
                    reply_to_message_id=reply_to,
                )

    except Exception as e:
        error_msg = f"😿 Erro no streaming: {str(e)[:200]}"
        if sent_message:
            try:
                await bot.edit_message_text(
                    error_msg,
                    chat_id=chat_id,
                    message_id=sent_message.message_id,
                )
            except Exception:
                pass
        else:
            await bot.send_message(chat_id, error_msg)

    return full_text


async def send_simple_message(chat_id: int, text: str, reply_to: int = None):
    """Envia uma mensagem simples. Se muito longa, envia como arquivo .md."""
    # Telegram limit: 4096 chars
    if len(text) > 3900:
        # Enviar como arquivo markdown
        await send_as_document(chat_id, text, reply_to=reply_to)
        return

    clean_text = sanitize_markdown(text)
    try:
        await bot.send_message(
            chat_id, clean_text,
            reply_to_message_id=reply_to,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        await bot.send_message(
            chat_id, text,
            reply_to_message_id=reply_to,
        )


async def send_as_document(chat_id: int, text: str, filename: str = None, reply_to: int = None):
    """Envia texto como arquivo .md no Telegram."""
    import tempfile
    import os
    from datetime import datetime
    from aiogram.types import FSInputFile

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pesquisa_{timestamp}.md"

    # Criar arquivo temporário
    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)

    try:
        doc = FSInputFile(tmp_path, filename=filename)
        # Enviar preview curto + arquivo
        preview = text[:300].split("\n")[0] + "..."
        await bot.send_document(
            chat_id,
            doc,
            caption=f"📄 {preview}",
            reply_to_message_id=reply_to,
        )
    except Exception as e:
        logger.error(f"Erro enviando documento: {e}")
        # Fallback: enviar em chunks
        for i in range(0, len(text), 3900):
            chunk = text[i:i+3900]
            try:
                await bot.send_message(chat_id, chunk)
            except Exception:
                pass
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def start_bot():
    """Inicia o bot Telegram (polling)."""
    logger.info("🌊 Telegram bot iniciando...")
    await dp.start_polling(bot)

--- END FILE ---

--- FILE: dashboard_api.py ---
import os
import asyncio
import collections
import logging
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import config
import core
import worker_protocol

app = FastAPI(title="Iara Dashboard API")

# Setup RingBuffer for logs (last 200 lines to allow scrolling)
class DequeLogHandler(logging.Handler):
    def __init__(self, maxlen=200):
        super().__init__()
        self.log_queue = collections.deque(maxlen=maxlen)
    
    def emit(self, record):
        msg = self.format(record)
        self.log_queue.append(msg)

# Register the handler
log_handler = DequeLogHandler(maxlen=200)
log_handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
logging.getLogger().addHandler(log_handler)

# Dirs
BASE_DIR = os.path.dirname(__file__)
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
RESEARCH_DIR = os.path.join(BASE_DIR, "research")
os.makedirs(DASHBOARD_DIR, exist_ok=True)
os.makedirs(RESEARCH_DIR, exist_ok=True)

# Mount static files (like JSONs or future assets if needed)
# Not serving index.html via StaticFiles directly to handle route cleanly
# app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

START_TIME = datetime.now()

@app.get("/")
async def get_index():
    index_path = os.path.join(DASHBOARD_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Index missing</h1>")

@app.get("/api/status")
async def get_status():
    working = await core.get_working_memory_count()
    episodes = await core.get_episode_count()
    uptime = datetime.now() - START_TIME
    uptime_str = str(uptime).split('.')[0] # Remove microsecs
    
    # Busca dados adicionais de bateria e RAM via termux (Master + Workers)
    system_info = await worker_protocol.get_all_system_status()
    
    return {
        "status": "online",
        "uptime": uptime_str,
        "working_messages": working,
        "episodes": episodes,
        "active_llm": config.LLM_PROVIDERS[0]["model"],
        "system_info": system_info
    }

@app.get("/api/logs")
async def get_logs():
    return JSONResponse(content={"logs": list(log_handler.log_queue)})

@app.get("/api/memory")
async def get_memory():
    facts = await core.get_core_memory()
    return {"core_facts": facts}

@app.get("/api/research")
async def get_research():
    if not os.path.exists(RESEARCH_DIR):
        return {"reports": []}
    files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md")]
    files.sort(reverse=True)  # Newest first
    return {"reports": files}

@app.get("/api/workers")
async def get_workers():
    # Convert workers dict to a safe format
    workers_info = []
    for name, data in worker_protocol._workers.items():
        workers_info.append({
            "name": name,
            "host": data.get("host", ""),
            "skills": data.get("skills", []),
            "status": data.get("status", "unknown"),
        })
    return {"workers": workers_info}

@app.get("/api/config")
async def get_config():
    safe_providers = []
    for p in config.LLM_PROVIDERS:
        safe_p = p.copy()
        if "api_key" in safe_p:
            key = safe_p["api_key"]
            if key and len(key) > 8:
                safe_p["api_key"] = f"{key[:4]}...{key[-4:]}"
            else:
                safe_p["api_key"] = "***"
        safe_providers.append(safe_p)
    
    return {"llm_providers": safe_providers}

from pydantic import BaseModel
class ChatRequest(BaseModel):
    text: str

from fastapi.responses import StreamingResponse
import brain

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # Salvar user message em working memory (opcional/pode ignorar pra não misturar com Telegram)
    # await core.save_message("user", request.text)
    
    # Executar tools para obter status do celular, pesquisas web, etc.
    tool_context, intent, query = await brain.execute_tools(request.text)
    
    system_prompt = await brain.build_system_prompt()
    conversation = await core.get_conversation()
    messages = [
        {"role": "system", "content": system_prompt + tool_context},
        *conversation,
        {"role": "user", "content": request.text}
    ]
    
    stream = brain.router.generate_stream(messages)
    
    async def event_generator():
        try:
            full_response = ""
            async for chunk in stream:
                full_response += chunk
                # Server-Sent Events (SSE) format
                yield f"data: {chunk}\n\n"
            
            # Save assistant response
            # await core.save_message("assistant", full_response)
        except Exception as e:
            yield f"data: [ERRO: {str(e)}]\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

def run_dashboard():
    # Only show critical errors in uvicorn format so it doesn't spam Iara's log
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")

--- END FILE ---

--- FILE: dashboard/index.html ---
<!DOCTYPE html>
<html lang="pt-BR">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌊 IARA Dashboard</title>
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-panel: #1e293b;
            --bg-header: #020617;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --border: #334155;
            --success: #22c55e;
            --warning: #f59e0b;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar */
        .sidebar {
            width: 250px;
            background-color: var(--bg-header);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }

        .logo {
            padding: 20px;
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--accent);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .nav-items {
            list-style: none;
            padding: 0;
            margin: 0;
            flex: 1;
        }

        .nav-item {
            padding: 15px 20px;
            cursor: pointer;
            border-bottom: 1px solid rgba(51, 65, 85, 0.5);
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .nav-item:hover {
            background-color: var(--bg-panel);
        }

        .nav-item.active {
            background-color: var(--bg-panel);
            color: var(--accent);
            border-left: 4px solid var(--accent);
        }

        /* Main Content */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .header {
            padding: 20px;
            background-color: var(--bg-panel);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(34, 197, 94, 0.1);
            color: var(--success);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--success);
        }

        .content-area {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }

        /* Views */
        .view {
            display: none;
            animation: fadeIn 0.3s;
        }

        .view.active {
            display: block;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(5px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Cards & Grids */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }

        .card {
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
        }

        .card h3 {
            margin-top: 0;
            color: var(--text-muted);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .card .value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--text-main);
            margin: 10px 0 0 0;
        }

        /* Logs specific styles */
        .logs-container {
            background: #000;
            border-radius: 8px;
            border: 1px solid var(--border);
            padding: 15px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.85rem;
            height: calc(100vh - 180px);
            /* Fill remaining space */
            overflow-y: auto;
            color: #e2e8f0;
            user-select: text;
            /* Allow copying */
        }

        .log-line {
            margin: 0 0 4px 0;
            white-space: pre-wrap;
            word-wrap: break-word;
            padding-bottom: 4px;
            border-bottom: 1px dashed #1e293b;
        }

        .log-line.error {
            color: #f87171;
        }

        .log-line.warning {
            color: #fbbf24;
        }

        .log-line.info {
            color: #38bdf8;
        }

        .toolbar {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            align-items: center;
        }

        /* Common table/list styles */
        .data-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .data-item {
            padding: 12px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
        }

        .data-item:last-child {
            border-bottom: none;
        }

        .file-link {
            color: var(--accent);
            text-decoration: none;
        }

        .file-link:hover {
            text-decoration: underline;
        }

        /* Chat styles */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 120px);
            background: var(--bg-panel);
            border-radius: 8px;
            border: 1px solid var(--border);
            overflow: hidden;
        }

        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 8px;
            line-height: 1.5;
            word-wrap: break-word;
        }

        .message p {
            margin: 0 0 10px 0;
        }

        .message p:last-child {
            margin: 0;
        }

        .message pre {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }

        .message code {
            font-family: 'Consolas', monospace;
            font-size: 0.9em;
        }

        .message.user {
            background: var(--accent);
            color: #000;
            align-self: flex-end;
            border-bottom-right-radius: 0;
        }

        .message.assistant {
            background: rgba(51, 65, 85, 0.5);
            color: var(--text-main);
            align-self: flex-start;
            border-bottom-left-radius: 0;
            border: 1px solid var(--border);
        }

        .chat-input-area {
            display: flex;
            padding: 15px;
            background: rgba(15, 23, 42, 0.5);
            border-top: 1px solid var(--border);
            gap: 10px;
        }

        .chat-input {
            flex: 1;
            background: var(--bg-dark);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 12px 15px;
            border-radius: 8px;
            font-size: 1rem;
            resize: none;
            outline: none;
        }

        .chat-input:focus {
            border-color: var(--accent);
        }

        .chat-send-btn {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 0 25px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 1rem;
            transition: background 0.2s;
        }

        .chat-send-btn:hover {
            background: var(--accent-hover);
        }

        .chat-send-btn:disabled {
            background: var(--border);
            cursor: not-allowed;
            color: var(--text-muted);
        }

        .file-link:hover {
            text-decoration: underline;
        }
    </style>
</head>

<body>

    <aside class="sidebar">
        <div class="logo">🌊 IARA</div>
        <ul class="nav-items">
            <li class="nav-item active" onclick="switchTab('status')">📊 Visão Geral</li>
            <li class="nav-item" onclick="switchTab('chat')">💬 Chat com IA</li>
            <li class="nav-item" onclick="switchTab('logs')">📋 Logs do Sistema</li>
            <li class="nav-item" onclick="switchTab('memory')">🧠 Core Memory</li>
            <li class="nav-item" onclick="switchTab('research')">🔬 Biblioteca de Pesquisas</li>
            <li class="nav-item" onclick="switchTab('workers')">🐝 Workers (Swarms)</li>
            <li class="nav-item" onclick="switchTab('config')">⚙️ Configurações</li>
        </ul>
    </aside>

    <main class="main-content">
        <header class="header">
            <h2 id="page-title" style="margin: 0;">Visão Geral</h2>
            <div class="status-badge" id="header-status">
                <div class="status-dot"></div>
                VIVO (Uptime: --)
            </div>
        </header>

        <div class="content-area">

            <!-- VIEW: STATUS -->
            <div id="view-status" class="view active">
                <div class="grid">
                    <div class="card">
                        <h3>Mensagens na RAM (Working)</h3>
                        <div class="value" id="stat-working">--</div>
                    </div>
                    <div class="card">
                        <h3>Episódios Salvos (Episodic)</h3>
                        <div class="value" id="stat-episodes">--</div>
                    </div>
                    <div class="card">
                        <h3>LLM Ativo</h3>
                        <div class="value" id="stat-llm" style="font-size: 1.5rem; color: var(--accent);">--</div>
                    </div>
                    <div class="card" style="grid-column: 1 / -1;">
                        <h3>Status dos Dispositivos (Bateria, Storage, RAM, CPU)</h3>
                        <pre id="stat-system"
                            style="margin-top: 15px; color: var(--text-muted); font-family: 'Consolas', monospace; white-space: pre-wrap; font-size: 0.95rem;">Aguardando dados...</pre>
                    </div>
                </div>
            </div>

            <!-- VIEW: CHAT -->
            <div id="view-chat" class="view">
                <div class="chat-container">
                    <div class="chat-messages" id="chat-messages">
                        <div class="message assistant">
                            👋 Olá! Sou a Iara. O que vamos criar hoje?
                        </div>
                    </div>
                    <div class="chat-input-area">
                        <textarea class="chat-input" id="chat-input" rows="2"
                            placeholder="Digite sua mensagem (Shift+Enter para nova linha)..."></textarea>
                        <button class="chat-send-btn" id="chat-send-btn" onclick="sendChatMessage()">Enviar</button>
                    </div>
                </div>
            </div>

            <!-- VIEW: LOGS -->
            <div id="view-logs" class="view">
                <div class="toolbar">
                    <div>
                        <input type="checkbox" id="auto-refresh-logs" checked>
                        <label for="auto-refresh-logs">Auto-scroll & Refresh (5s)</label>
                    </div>
                    <button onclick="fetchLogs()"
                        style="background:var(--accent); color:#000; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">Atualizar
                        Manualmente</button>
                </div>
                <div class="logs-container" id="logs-output">
                    Carregando logs...
                </div>
            </div>

            <!-- VIEW: MEMORY -->
            <div id="view-memory" class="view">
                <div class="card">
                    <ul class="data-list" id="memory-list">
                        <li class="data-item text-muted">Carregando fatos permanentes...</li>
                    </ul>
                </div>
            </div>

            <!-- VIEW: RESEARCH -->
            <div id="view-research" class="view">
                <div class="card">
                    <h3>Relatórios Salvos C:\Users\marce\Desktop\projetin\research</h3>
                    <ul class="data-list" id="research-list">
                        <li class="data-item text-muted">Carregando pesquisas...</li>
                    </ul>
                </div>
            </div>

            <!-- VIEW: WORKERS -->
            <div id="view-workers" class="view">
                <div class="grid" id="workers-grid">
                    Carregando workers...
                </div>
            </div>

            <!-- VIEW: CONFIG -->
            <div id="view-config" class="view">
                <div class="card">
                    <h3>Provedores LLM (Cascata)</h3>
                    <ul class="data-list" id="config-list">
                        <li class="data-item text-muted">Carregando config...</li>
                    </ul>
                </div>
            </div>

        </div>
    </main>

    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        let currentTab = 'status';
        let refreshInterval = null;

        const tabTitles = {
            'status': 'Visão Geral',
            'chat': 'Chat com Iara',
            'logs': 'Logs do Sistema',
            'memory': 'Core Memory',
            'research': 'Biblioteca de Pesquisas',
            'workers': 'Workers (Swarms)',
            'config': 'Configurações'
        };

        function switchTab(tabId) {
            // Update UI
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            event.currentTarget.classList.add('active');

            document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
            document.getElementById('view-' + tabId).classList.add('active');

            document.getElementById('page-title').innerText = tabTitles[tabId];
            currentTab = tabId;

            // Fetch data immediately for the new tab
            fetchDataForTab();
        }

        async function fetchDataForTab() {
            try {
                if (currentTab === 'status') await fetchStatus();
                else if (currentTab === 'logs') await fetchLogs();
                else if (currentTab === 'memory') await fetchMemory();
                else if (currentTab === 'research') await fetchResearch();
                else if (currentTab === 'workers') await fetchWorkers();
                else if (currentTab === 'config') await fetchConfig();
            } catch (err) {
                console.error("Erro ao buscar dados:", err);
            }
        }

        // --- FETCHERS ---
        async function fetchStatus() {
            const res = await fetch('/api/status');
            const data = await res.json();
            document.getElementById('stat-working').innerText = data.working_messages;
            document.getElementById('stat-episodes').innerText = data.episodes;
            document.getElementById('stat-llm').innerText = data.active_llm;
            document.getElementById('header-status').innerHTML = `<div class="status-dot"></div> VIVO (Uptime: ${data.uptime})`;

            if (data.system_info) {
                document.getElementById('stat-system').innerText = data.system_info;
            }
        }

        async function fetchLogs() {
            const autoRefresh = document.getElementById('auto-refresh-logs').checked;
            // Only auto-fetch if checked (when called by interval), but allow manual fetch
            if (!autoRefresh && event && event.type !== "click") return;

            const res = await fetch('/api/logs');
            const data = await res.json();
            const container = document.getElementById('logs-output');

            container.innerHTML = '';
            data.logs.forEach(line => {
                const p = document.createElement('p');
                p.className = 'log-line';
                if (line.includes('ERROR') || line.includes('WARNING')) p.classList.add('error');
                else if (line.includes('INFO')) p.classList.add('info');
                p.textContent = line;
                container.appendChild(p);
            });

            if (autoRefresh) {
                container.scrollTop = container.scrollHeight;
            }
        }

        async function fetchMemory() {
            const res = await fetch('/api/memory');
            const data = await res.json();
            const list = document.getElementById('memory-list');
            list.innerHTML = '';

            if (data.core_facts.length === 0) {
                list.innerHTML = '<li class="data-item text-muted">Sem fatos salvos.</li>';
                return;
            }

            data.core_facts.forEach(fact => {
                const li = document.createElement('li');
                li.className = 'data-item';
                li.innerHTML = `
                    <span style="flex:1;"><strong>[${fact.category}]</strong> ${fact.content}</span>
                    <span style="color:var(--text-muted); font-size:0.8rem;">Confiança: ${(fact.confidence * 100).toFixed(0)}%</span>
                `;
                list.appendChild(li);
            });
        }

        async function fetchResearch() {
            const res = await fetch('/api/research');
            const data = await res.json();
            const list = document.getElementById('research-list');
            list.innerHTML = '';

            if (data.reports.length === 0) {
                list.innerHTML = '<li class="data-item text-muted">Nenhuma pesquisa salva no servidor local.</li>';
                return;
            }

            data.reports.forEach(report => {
                const li = document.createElement('li');
                li.className = 'data-item';
                li.innerHTML = `<span>📄 ${report}</span> <span style="color:var(--text-muted)">Servidor Local</span>`;
                list.appendChild(li);
            });
        }

        async function fetchWorkers() {
            const res = await fetch('/api/workers');
            const data = await res.json();
            const grid = document.getElementById('workers-grid');
            grid.innerHTML = '';

            if (data.workers.length === 0) {
                grid.innerHTML = '<div class="card text-muted">Nenhum worker registrado via protocolo SSH.</div>';
                return;
            }

            data.workers.forEach(w => {
                const statusColor = w.status === 'online' ? 'var(--success)' : 'var(--warning)';
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between;">
                        <h3 style="color:var(--text-main); font-size:1.1rem; text-transform:none;">🐝 ${w.name}</h3>
                        <span style="color:${statusColor}; font-size:0.8rem; font-weight:bold;">${w.status.toUpperCase()}</span>
                    </div>
                    <div style="color:var(--text-muted); font-size:0.9rem; margin-top:10px;">
                        <div>Host: ${w.host}</div>
                        <div>Skills: ${w.skills.join(', ') || 'Todas'}</div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        async function fetchConfig() {
            const res = await fetch('/api/config');
            const data = await res.json();
            const list = document.getElementById('config-list');
            list.innerHTML = '';

            data.llm_providers.forEach((p, idx) => {
                const li = document.createElement('li');
                li.className = 'data-item';
                li.innerHTML = `
                    <div style="flex:1;">
                        <span style="font-weight:bold; color:var(--text-main);">${idx + 1}. ${p.name.toUpperCase()}</span>
                        <div style="color:var(--text-muted); font-size:0.85rem; margin-top:4px;">Modelo: ${p.model}</div>
                        <div style="color:var(--text-muted); font-size:0.85rem;">Base URL: ${p.base_url}</div>
                    </div>
                    <div style="text-align:right; color:var(--text-muted); font-size:0.85rem;">
                        <div>Streaming: ${p.supports_streaming ? '✅' : '❌'}</div>
                        <div>Tools: ${p.supports_tools ? '✅' : '❌'}</div>
                        <div style="margin-top:4px; font-family:monospace;">Key: ${p.api_key}</div>
                    </div>
                `;
                list.appendChild(li);
            });
        }

        // --- CHAT LOGIC ---
        const chatInput = document.getElementById('chat-input');
        chatInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });

        async function sendChatMessage() {
            const text = chatInput.value.trim();
            if (!text) return;

            const btn = document.getElementById('chat-send-btn');
            const messagesContainer = document.getElementById('chat-messages');

            // Add User Message
            const userDiv = document.createElement('div');
            userDiv.className = 'message user';
            userDiv.innerText = text;
            messagesContainer.appendChild(userDiv);

            chatInput.value = '';
            btn.disabled = true;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // Add Assistant Message Placeholder
            const asstDiv = document.createElement('div');
            asstDiv.className = 'message assistant';
            asstDiv.innerHTML = '<span style="color: var(--text-muted)">Pensando...</span>';
            messagesContainer.appendChild(asstDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });

                if (!response.body) throw new Error("Body is null");

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let mdContent = '';

                // Handle SSE
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data) {
                                mdContent += data;
                                // Parse Markdown safely handling unclosed tags during streaming
                                asstDiv.innerHTML = marked.parse(mdContent);
                                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                            }
                        }
                    }
                }
            } catch (err) {
                asstDiv.innerHTML = `<span style="color: var(--warning)">Erro ao comunicar: ${err.message}</span>`;
            } finally {
                btn.disabled = false;
                chatInput.focus();
            }
        }

        // Loop principal (polling 5s)
        setInterval(fetchDataForTab, 5000);

        // Initial load
        fetchDataForTab();

    </script>
</body>

</html>
--- END FILE ---
