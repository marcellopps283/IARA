import os
import asyncio
import collections
import logging
import shutil
from datetime import datetime
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import aiosqlite

import config
import core
import worker_protocol
import deep_research
import brain

app = FastAPI(title="Iara Dashboard API")

# ── Ring buffer de logs (últimas 200 linhas) ──────────────────────
class DequeLogHandler(logging.Handler):
    def __init__(self, maxlen=200):
        super().__init__()
        self.log_queue = collections.deque(maxlen=maxlen)

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.append(msg)

log_handler = DequeLogHandler(maxlen=200)
log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
))
logging.getLogger().addHandler(log_handler)

BASE_DIR = os.path.dirname(__file__)
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
RESEARCH_DIR = os.path.join(BASE_DIR, "research")
UPLOAD_DIR = "/tmp/iara_uploads"

os.makedirs(DASHBOARD_DIR, exist_ok=True)
os.makedirs(RESEARCH_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

START_TIME = datetime.now()

# ── Modelos Pydantic ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    text: str

class ResearchRequest(BaseModel):
    topic: str
    tipo: str | None = None

class MemoryFactRequest(BaseModel):
    category: str
    content: str

class TogglesRequest(BaseModel):
    cot: bool | None = None
    reflect: bool | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS EXISTENTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    uptime_str = str(uptime).split(".")[0]
    system_info = await worker_protocol.get_all_system_status()
    return {
        "status": "online",
        "uptime": uptime_str,
        "workingMessages": working,
        "episodes": episodes,
        "activeLlm": config.LLM_PROVIDERS[0]["model"],
        "systemInfo": system_info,
    }


@app.get("/api/logs")
async def get_logs():
    return JSONResponse(content={"logs": list(log_handler.log_queue)})


@app.get("/api/memory")
async def get_memory():
    facts = await core.get_core_memory()
    return {"coreFacts": facts}


@app.get("/api/research")
async def get_research():
    if not os.path.exists(RESEARCH_DIR):
        return {"reports": []}
    files_list = [f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md")]
    files_list.sort(reverse=True)
    return {"reports": files_list}


@app.get("/api/workers")
async def get_workers():
    workers_info = []
    for name, data in worker_protocol.workers.items():
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
        if "apiKey" in safe_p:
            key = safe_p["apiKey"]
            if key and len(key) > 8:
                safe_p["apiKey"] = f"{key[:4]}...{key[-4:]}"
        safe_providers.append(safe_p)
    return {
        "llmProviders": safe_providers,
        "cotEnabled": brain.cot_enabled,
        "reflectEnabled": brain.reflect_enabled,
    }


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_generator():
        try:
            yield "data: [STATUS] Interpretando intenção via Brain...\n\n"
            tool_context, intent, query = await brain.execute_tools(request.text)
            
            yield f"data: [STATUS] Intent detectada: [{intent.upper()}]\n\n"
            yield "data: [THINKING] Consolidando contexto da memória e tools...\n\n"
            
            system_prompt = await brain.build_system_prompt()
            conversation = await core.get_conversation()
            messages = [
                {"role": "system", "content": system_prompt + tool_context},
                *conversation,
                {"role": "user", "content": request.text},
            ]
            
            yield "data: [STATUS] Inicializando LLM Router (Streaming)...\n\n"
            stream = brain.router.generate_stream(messages)
            
            yield "data: [ANSWER]\n\n"
            async for chunk in stream:
                yield f"data: {chunk}\n\n"
                
        except RuntimeError as re:
            # Pega erros de cota do HITL Policy ou do router
            yield f"data: [ERRO CRÍTICO] {str(re)}\n\n"
        except Exception as e:
            yield f"data: [ERRO] {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS NOVOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    filepath = os.path.join(UPLOAD_DIR, file.filename or "arquivo")
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filepath": filepath, "filename": file.filename}


@app.post("/api/research/start")
async def start_research(request: ResearchRequest):
    router = brain.router

    async def event_stream():
        try:
            # Fase 1: criar plano
            plan = await deep_research.create_plan(request.topic, router)
            tipo = plan.get("tipo", "EXPLORATÓRIA") if isinstance(plan, dict) else "EXPLORATÓRIA"

            # Fase 2: executar com coleta de progresso
            collected_progress = []

            async def collect_progress(msg: str):
                collected_progress.append(msg)

            all_data, sources = await deep_research.execute_plan(
                request.topic, plan, router,
                progress_cb=collect_progress,
            )

            # Envia todos os updates de progresso acumulados
            for msg in collected_progress:
                clean = msg.replace("\n", " ").strip()
                yield f"data: {clean}\n\n"

            # Marcador que sinaliza ao frontend: a partir daqui é o relatório
            yield "data: [REPORT_START]\n\n"

            # Fase 3: síntese
            report = await deep_research.synthesize_with_citations(
                request.topic, all_data, sources, router, tipo=tipo
            )

            # Envia o relatório em chunks de 300 chars (aparece progressivamente)
            chunk_size = 300
            for i in range(0, len(report), chunk_size):
                yield f"data: {report[i:i+chunk_size]}\n\n"

        except Exception as e:
            yield f"data: [ERRO] {str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/research/{filename}")
async def get_research_content(filename: str):
    # Segurança: bloqueia path traversal
    if ".." in filename or "/" in filename:
        return JSONResponse(status_code=400, content={"error": "Nome inválido"})
    filepath = os.path.join(RESEARCH_DIR, filename)
    if not os.path.exists(filepath):
        return JSONResponse(status_code=404, content={"error": "Relatório não encontrado"})
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content)


@app.delete("/api/memory/{fact_id}")
async def delete_memory_fact(fact_id: int):
    async with aiosqlite.connect(str(config.DB_PATH)) as db:
        await db.execute("DELETE FROM core_memory WHERE id = ?", (fact_id,))
        await db.commit()
    return {"ok": True}


@app.post("/api/memory")
async def add_memory_fact(request: MemoryFactRequest):
    await core.save_core_fact(request.category, request.content)
    return {"ok": True}


@app.post("/api/config/toggles")
async def set_toggles(request: TogglesRequest):
    if request.cot is not None:
        brain.cot_enabled = request.cot
    if request.reflect is not None:
        brain.reflect_enabled = request.reflect
    return {"cot": brain.cot_enabled, "reflect": brain.reflect_enabled}


# ── Servir build do React em produção ────────────────────
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")


def run_dashboard():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
