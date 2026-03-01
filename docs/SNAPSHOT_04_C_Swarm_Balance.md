
--- FILE: orchestrator.py ---
"""
orchestrator.py — Gerente Burocrático do Swarm (ZeroClaw)
Mantém fila de tarefas, prioriza o S21 FE e previne OOM no S21 Ultra.
Trabalha com Personas Estáticas pré-definidas na pasta /roles/.
"""

import asyncio
import logging
from typing import Dict, Any, List

import config
import worker_protocol
import core

logger = logging.getLogger("orchestrator")

# Tabela de controle de processos ativos (quantos agentes em cada nó)
_active_workers: Dict[str, int] = {
    "S21FE": 0,
    "KittyS21": 0  # S21 Ultra (Master overflow)
}

# Fila de espera global
_task_queue = asyncio.Queue()


class SwarmTask:
    def __init__(self, role_name: str, payload: str, callback=None, job_id: int = None):
        self.role_name = role_name
        self.payload = payload
        self.callback = callback  # Função para avisar a Iara quando a task terminar
        self.job_id = job_id  # Controle do SQLite para anti-crash


def _get_available_node() -> str | None:
    """Retorna o nó disponível com maior prioridade, ou None se tudo lotado."""
    # Prioridade 1: S21 FE
    workers = {w['name']: w for w in worker_protocol.get_workers()}
    
    if "S21FE" in workers and _active_workers["S21FE"] < config.MAX_WORKERS_S21FE:
        return "S21FE"
    
    # Prioridade 2: Ultra (transbordo)
    if _active_workers["KittyS21"] < config.MAX_WORKERS_ULTRA:
        return "KittyS21"
    
    return None


async def load_pending_jobs():
    """Chamado na inicialização para recuperar jobs perdidos em caso de crash (Amnésia)."""
    try:
        jobs = await core.get_pending_swarm_jobs()
        for job in jobs:
            task = SwarmTask(job['role_name'], job['payload'], None, job_id=job['id'])
            await _task_queue.put(task)
        if jobs:
            logger.info(f"♻️ Recuperados {len(jobs)} jobs perdentes do SQLite pós-crash!")
            asyncio.create_task(_process_queue())
    except Exception as e:
        logger.error(f"Erro ao recuperar fila do SQLite: {e}")

async def submit_task(role_name: str, payload: str, callback=None):
    """A Iara chama isso para jogar trabalho no Orquestrador."""
    # Persiste no SQLite primeiro
    job_id = await core.add_swarm_job(role_name, payload)
    
    task = SwarmTask(role_name, payload, callback, job_id=job_id)
    await _task_queue.put(task)
    logger.info(f"📋 Task '{role_name}' adicionada à fila DB-ID #{job_id} (Tamanho: {_task_queue.qsize()})")
    
    # Garante que o loop do orchestrator comece a esvaziar a fila se já não estiver
    asyncio.create_task(_process_queue())


async def _process_queue():
    """Inspeciona a fila e despacha para os workers disponíveis."""
    while not _task_queue.empty():
        target_node = _get_available_node()
        
        if not target_node:
            logger.warning("🧱 Enxame lotado (OOM Defense Ativado). Aguardando slots...")
            break  # Sai do processamento agora, será chamado de novo quando um worker liberar
        
        task: SwarmTask = await _task_queue.get()
        _active_workers[target_node] += 1
        
        logger.info(f"🚀 Deployando persona '{task.role_name}' no nó >>> {target_node} <<< (Job #{task.job_id})")
        
        if task.job_id:
            await core.update_swarm_job_status(task.job_id, 'processing')
        
        # Lança a execução desanexada
        asyncio.create_task(_execute_on_node(target_node, task))


async def _execute_on_node(node_name: str, task: SwarmTask):
    """Executa a tarefa no nó via worker_protocol SSH."""
    result = None
    status = "done"
    try:
        # Chama SSH pra acionar o run_task.py do worker com a persona específica
        result = await worker_protocol.dispatch_mini_agent(node_name, task.role_name, task.payload)
        
        if isinstance(result, str) and result.startswith("Falha"):
            status = "failed"
            
    except Exception as e:
        logger.error(f"❌ Erro executando mini-agente no {node_name}: {e}")
        result = f"Error: {e}"
        status = "failed"
    finally:
        # Registra sucesso ou falha no SQLite persistente
        if task.job_id:
            res_str = str(result)[:500] if result else ""
            await core.update_swarm_job_status(task.job_id, status, res_str)
            
        # Libera o slot do worker
        _active_workers[node_name] -= 1
        logger.info(f"🏁 Task #{task.job_id} concluída. Slot devolvido no {node_name}. Ativos lá: {_active_workers[node_name]}")
        
        if task.callback:
            await task.callback(result)
            
        # Como liberou espaço, tenta processar mais da fila
        asyncio.create_task(_process_queue())

--- END FILE ---

--- FILE: worker_protocol.py ---
"""
worker_protocol.py — Protocolo de delegação de tarefas via SSH
Envia tarefas para workers remotos, recebe resultado via stdout.
"""

import asyncio
import json
import logging
import os

logger = logging.getLogger("worker_protocol")

# Registry de workers configurados
# Formato: {"nome": {"host": "ssh_alias_ou_ip", "skills": ["search", "llm", ...], "online": True}}
_workers: dict = {
    "S21FE": {
        "host": "S21FE",
        "skills": ["search", "llm", "deep_read"],
        "online": False
    }
}


def register_worker(name: str, host: str, skills: list[str] = None):
    """Registra um worker no swarm."""
    _workers[name] = {
        "host": host,
        "skills": skills or ["search", "llm", "deep_read"],
        "online": True,
    }
    logger.info(f"🐝 Worker registrado: {name} ({host}) — skills: {skills}")


def remove_worker(name: str):
    """Remove um worker do swarm."""
    if name in _workers:
        del _workers[name]
        logger.info(f"🐝 Worker removido: {name}")


def get_workers(skill: str = None) -> list[dict]:
    """Retorna workers disponíveis, opcionalmente filtrados por skill."""
    result = []
    for name, info in _workers.items():
        if not info["online"]:
            continue
        if skill and skill not in info["skills"]:
            continue
        result.append({"name": name, **info})
    return result


def list_all_workers() -> str:
    """Retorna status formatado de todos os workers."""
    if not _workers:
        return "Nenhum worker registrado. Use `/worker add nome host` pra adicionar."

    lines = ["🐝 **Workers registrados:**\n"]
    for name, info in _workers.items():
        status = "🟢 online" if info["online"] else "🔴 offline"
        skills = ", ".join(info["skills"])
        lines.append(f"• **{name}** — {info['host']} — {status}\n  Skills: {skills}")
    return "\n".join(lines)


async def delegate(host: str, task: dict, timeout: int = 60) -> dict:
    """
    Delega uma tarefa para um worker via SSH.
    
    Args:
        host: SSH alias ou user@ip do worker
        task: Dict com {"type": "search|llm|deep_read|analyze", ...}
        timeout: Tempo máximo de execução
    
    Returns:
        Dict com resultado ou erro
    """
    task_json = json.dumps(task, ensure_ascii=False)
    logger.info(f"📤 Delegando para {host}: {task.get('type', '?')}")

    try:
        if host == "localhost":
            proc = await asyncio.create_subprocess_exec(
                "python", os.path.expanduser("~/KittyClaw/run_task.py"), # Ultra's directory
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                "ssh", 
                "-o", "ServerAliveInterval=15",
                "-o", "ServerAliveCountMax=3",
                host, "python", "~/IaraWorker/run_task.py",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=task_json.encode("utf-8")),
            timeout=timeout,
        )

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[:500]
            logger.error(f"❌ Worker {host} erro: {error_msg}")
            return {"error": f"Worker falhou: {error_msg}"}

        result_text = stdout.decode("utf-8", errors="replace").strip()

        # Tentar parsear JSON do stdout
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # Se não é JSON, retorna como texto
            return {"result": result_text}

    except asyncio.TimeoutError:
        logger.error(f"⏰ Worker {host} timeout ({timeout}s)")
        return {"error": f"Worker timeout após {timeout}s"}
    except Exception as e:
        logger.error(f"❌ Falha SSH para {host}: {e}")
        # Marcar worker como offline
        for name, info in _workers.items():
            if info["host"] == host:
                info["online"] = False
                logger.warning(f"🔴 Worker {name} marcado offline")
        return {"error": f"SSH falhou: {str(e)[:200]}"}



async def delegate_parallel(workers: list[dict], tasks: list[dict], timeout: int = 60) -> list[dict]:
    """
    Fan-out: delega múltiplas tarefas para múltiplos workers em paralelo.
    
    Args:
        workers: Lista de workers (de get_workers())
        tasks: Lista de tasks (mesmo tamanho que workers)
        timeout: Timeout por task
    
    Returns:
        Lista de resultados (mesma ordem que tasks)
    """
    coros = []
    for worker, task in zip(workers, tasks):
        coros.append(delegate(worker["host"], task, timeout))

    results = await asyncio.gather(*coros, return_exceptions=True)

    # Converter exceções em dicts de erro
    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            clean_results.append({"error": str(r)})
        else:
            clean_results.append(r)

    return clean_results


async def dispatch_mini_agent(node_name: str, role_name: str, payload: str, timeout: int = 300) -> str:
    """
    Envia uma instrução para ser executada por uma Persona Estática em um nó específico.
    Usado pelo orchestrator.py
    """
    host = None
    if node_name == "S21FE" and "S21FE" in _workers:
        host = _workers["S21FE"]["host"]
    elif node_name == "KittyS21":
        host = "localhost" # O Master roda nele mesmo
    else:
        # Se não achou na config hardcoded, tenta achar no dict normal
        if node_name in _workers:
            host = _workers[node_name]["host"]
            
    if not host:
        return f"Error: Node {node_name} offline ou não encontrado."
        
    task_json = {
        "type": "mini_agent",
        "role": role_name,
        "payload": payload
    }
    
    logger.info(f"🎭 Fazendo deploy do Mini-Agente '{role_name}' para o nó {node_name}")
    
    result = await delegate(host, task_json, timeout=timeout)
    
    if "error" in result:
        logger.error(f"Erro no mini-agente no {node_name}: {result['error']}")
        return f"Falha no Agente: {result['error']}"
        
    return result.get("result", str(result))



async def health_check():
    """Verifica quais workers estão online via SSH ping."""
    for name, info in _workers.items():
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-o", "ConnectTimeout=5", 
                "-o", "ServerAliveInterval=5",
                "-o", "ServerAliveCountMax=2",
                info["host"], "echo", "ok",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            was_online = info["online"]
            info["online"] = proc.returncode == 0

            if info["online"] and not was_online:
                logger.info(f"🟢 Worker {name} voltou online")
            elif not info["online"] and was_online:
                logger.warning(f"🔴 Worker {name} ficou offline")
        except Exception:
            info["online"] = False

async def get_all_system_status() -> str:
    """Retorna o status do sistema do master (S21 Ultra) e todos os workers online."""
    import core
    
    # 1. Status do Master
    master_task = asyncio.create_task(core.get_system_status())
    
    # 2. Status dos Workers
    active_workers = get_workers()
    worker_tasks = [{"type": "status"} for _ in active_workers]
    
    master_status = await master_task
    
    parts = [f"🌊 IARA (S21 Ultra):\n  {master_status}"]
    
    if active_workers:
        results = await delegate_parallel(active_workers, worker_tasks, timeout=10)
        for w, res in zip(active_workers, results):
            name = w["name"]
            if "error" in res:
                parts.append(f"🐝 {name} ({w['host']}):\n  Erro: {res['error']}")
            else:
                status_str = res.get("result", "Sem dados")
                parts.append(f"🐝 {name} ({w['host']}):\n  {status_str}")
                
    return "\n\n".join(parts)

--- END FILE ---

--- FILE: llm_router.py ---
"""
llm_router.py — Roteador multi-LLM com fallback automático
Usa aiohttp com a API REST compatível com OpenAI (sem SDK compilado).
Compatível com Termux/Android (sem jiter/C extensions).
"""

import asyncio
import json
import logging
import random
from typing import AsyncGenerator

import aiohttp

import config

logger = logging.getLogger("llm_router")

# Limita requisições LLM simultâneas (evita bans por HTTP 429 Timeouts)
_api_semaphore = asyncio.Semaphore(3)


class LLMRouter:
    """
    Gerencia múltiplos provedores de LLM com fallback automático.
    
    Tenta o provedor primário (Groq). Se falhar (rate limit, timeout, erro),
    automaticamente tenta o próximo da lista. Suporta streaming.
    """

    def __init__(self):
        self.providers = []
        self._init_providers()
        self.current_provider = None

    def _init_providers(self):
        """Inicializa providers apenas com API key configurada."""
        for provider in config.LLM_PROVIDERS:
            if not provider["api_key"]:
                logger.info(f"⏭️ Provider '{provider['name']}' sem API key, pulando.")
                continue
            self.providers.append(provider)
            logger.info(f"✅ Provider '{provider['name']}' ({provider['model']}) configurado.")

        if not self.providers:
            raise RuntimeError("❌ Nenhum provider de LLM configurado! Verifique o .env")

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> str | dict:
        """
        Gera uma resposta usando o primeiro provider disponível.
        Se falhar, faz fallback para o próximo.
        
        Returns:
            Texto da resposta OU dict com tool_calls.
        """
        last_error = None

        for provider in self.providers:
            try:
                logger.info(f"🧠 Tentando: {provider['name']} ({provider['model']})")
                self.current_provider = provider["name"]

                body = {
                    "model": provider["model"],
                    "messages": messages,
                    "max_tokens": provider["max_tokens"],
                    "temperature": temperature,
                    "stream": False,
                }

                if tools and provider.get("supports_tools"):
                    body["tools"] = tools
                    body["tool_choice"] = "auto"

                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                }

                url = f"{provider['base_url']}/chat/completions"
                timeout = aiohttp.ClientTimeout(total=config.LLM_TIMEOUT_SECONDS)

                max_retries = 3
                for attempt in range(max_retries):
                    async with _api_semaphore:
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(url, headers=headers, json=body) as resp:
                                if resp.status == 429:
                                    wait_time = (2 ** attempt) + random.uniform(0.1, 1.5)
                                    logger.warning(f"⚠️ {provider['name']}: Rate limit (429). Retry {attempt+1}/{max_retries} in {wait_time:.1f}s")
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(wait_time)
                                        continue
                                    else:
                                        break # Vai pro fallback (próximo provider)
                                        
                                if resp.status != 200:
                                    error_text = await resp.text()
                                    logger.warning(f"⚠️ {provider['name']}: HTTP {resp.status} - {error_text[:200]}")
                                    break # Erros normais não dão retry, fazemos fallback

                                data = await resp.json()

                                choice = data["choices"][0]
                                message = choice["message"]

                                # Se o modelo quer chamar tools
                                if choice.get("finish_reason") == "tool_calls" or message.get("tool_calls"):
                                    return message  # Retorna o dict completo

                                return message.get("content", "")

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ {provider['name']}: Timeout ({config.LLM_TIMEOUT_SECONDS}s)")
                last_error = f"Timeout em {provider['name']}"
                continue
            except Exception as e:
                logger.warning(f"⚠️ {provider['name']} falhou: {str(e)[:200]}")
                last_error = str(e)
                continue

        raise RuntimeError(f"❌ Todos os providers falharam. Último: {last_error}")

    async def generate_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Gera resposta em streaming (token por token via SSE).
        Faz fallback automático se o provider falhar.
        """
        last_error = None

        for provider in self.providers:
            if not provider.get("supports_streaming"):
                continue

            try:
                logger.info(f"🌊 Streaming via: {provider['name']} ({provider['model']})")
                self.current_provider = provider["name"]

                body = {
                    "model": provider["model"],
                    "messages": messages,
                    "max_tokens": provider["max_tokens"],
                    "temperature": temperature,
                    "stream": True,
                }

                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                }

                url = f"{provider['base_url']}/chat/completions"
                timeout = aiohttp.ClientTimeout(total=config.LLM_TIMEOUT_SECONDS)

                max_retries = 3
                for attempt in range(max_retries):
                    async with _api_semaphore:
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(url, headers=headers, json=body) as resp:
                                if resp.status == 429:
                                    wait_time = (2 ** attempt) + random.uniform(0.1, 1.5)
                                    logger.warning(f"⚠️ Streaming {provider['name']}: Rate limit (429). Retry {attempt+1}/{max_retries} in {wait_time:.1f}s")
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(wait_time)
                                        continue
                                    else:
                                        break # Vai pro fallback

                                if resp.status != 200:
                                    error_text = await resp.text()
                                    logger.warning(f"⚠️ Streaming {provider['name']}: HTTP {resp.status}")
                                    last_error = error_text[:200]
                                    break

                                # Parse SSE stream
                                async for line in resp.content:
                                    line = line.decode("utf-8").strip()
                                    if not line or not line.startswith("data: "):
                                        continue
                                    
                                    data_str = line[6:]  # Remove "data: "
                                    if data_str == "[DONE]":
                                        return

                                    try:
                                        data = json.loads(data_str)
                                        delta = data["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                    except (json.JSONDecodeError, KeyError, IndexError):
                                        continue

                return  # Stream completou

            except Exception as e:
                logger.warning(f"⚠️ Streaming '{provider['name']}' falhou: {str(e)[:200]}")
                last_error = str(e)
                continue

        # Se streaming falhou, tenta sem stream
        logger.warning("⚠️ Streaming falhou em todos, tentando sem stream...")
        try:
            result = await self.generate(messages, temperature=temperature)
            if isinstance(result, str):
                yield result
        except Exception as e:
            yield f"😿 Desculpa Criador, todos os meus cérebros falharam. Erro: {str(e)[:100]}"

    def get_status(self) -> dict:
        """Retorna status dos providers configurados."""
        return {
            "providers_ativos": [p["name"] for p in self.providers],
            "provider_atual": self.current_provider,
            "total_providers": len(self.providers),
        }

--- END FILE ---
