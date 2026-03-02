"""
worker_protocol.py — Protocolo de delegação de tarefas via SSH
Envia tarefas para workers remotos, recebe resultado via stdout.
"""

import asyncio
import json
import logging
import os
import tailscale_discovery

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
                "-o", "StrictHostKeyChecking=no",  # crucial when IP changes
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
            error_msg = stderr.decode("utf-8", errors="replace")
            # --- INCÍCIO DO TAILSCALE FALLBACK ---
            logger.warning(f"⚠️ SSH '{host}' falhou. Código {proc.returncode}. Puxando Tailscale Discovery...")
            
            # Se a string host for o nome original (ex S21FE), tentamos achar o IP da tailnet
            # Se quisermos, iteramos pelo _workers pra achar a key real pra jogar no CLI
            target_hostname = host
            for name, info in _workers.items():
                if info["host"] == host: target_hostname = name
                
            new_ip = await tailscale_discovery.get_tailscale_ip(target_hostname)
            
            if new_ip and new_ip != host:
                logger.info(f"🔄 Magia do Tailscale! Rota nova recuperada: {new_ip}. Retentando...")
                # Atualizar registry global 
                for name, info in _workers.items():
                    if info["host"] == host:
                        info["host"] = new_ip
                        
                proc2 = await asyncio.create_subprocess_exec(
                    "ssh", 
                    "-o", "ServerAliveInterval=15",
                    "-o", "ServerAliveCountMax=3",
                    "-o", "StrictHostKeyChecking=no",
                    new_ip, "python", "~/IaraWorker/run_task.py",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                stdout, stderr = await asyncio.wait_for(
                    proc2.communicate(input=task_json.encode("utf-8")),
                    timeout=timeout,
                )
                
                if proc2.returncode != 0:
                    final_err = stderr.decode("utf-8", errors="replace")[:500]
                    logger.error(f"❌ Worker no IP '{new_ip}' falhou em definitivo: {final_err}")
                    return {"error": f"Worker falhou mesmo na rota tailscale: {final_err}"}
                    
            else:
                logger.error(f"❌ Worker {host} erro: {error_msg[:500]}")
                return {"error": f"Worker falhou: {error_msg[:500]}"}
            # --- FIM DO TAILSCALE FALLBACK ---

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
        logger.error(f"❌ Falha no despachante SSH para {host}: {e}")
        for name, info in _workers.items():
            if info["host"] == host:
                info["online"] = False
                logger.warning(f"🔴 Worker {name} marcado offline devida a grande falha.")
        return {"error": f"Exceção catastrófica de despachante SSH: {str(e)[:200]}"}



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
