#!/usr/bin/env python3
"""
run_task.py — Executor de tarefas no worker
Recebe JSON via stdin, executa, retorna JSON via stdout.

Este arquivo deve ser copiado para ~/IaraWorker/ em cada worker,
junto com web_search.py e um .env com API keys próprias.

Uso: echo '{"type":"search","query":"test"}' | python run_task.py
"""

import asyncio
import json
import os
import sys
import logging

# Setup mínimo — worker não precisa de toda a infra do Ultra
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("worker")

# Carregar .env local do worker
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/IaraWorker/.env"))


async def handle_task(task: dict) -> dict:
    """Executa uma tarefa baseado no tipo."""
    task_type = task.get("type", "")

    if task_type == "search":
        return await _do_search(task)
    elif task_type == "deep_read":
        return await _do_deep_read(task)
    elif task_type == "llm_generate":
        return await _do_llm_generate(task)
    elif task_type == "ping":
        return {"status": "ok", "node": os.uname().nodename}
    elif task_type == "status":
        return await _do_get_status(task)
    elif task_type == "mini_agent":
        return await _handle_mini_agent(task)
    else:
        return {"error": f"Tipo de tarefa desconhecido: {task_type}"}

async def _handle_mini_agent(task: dict) -> dict:
    """Carrega uma persona do disco e executa o payload via LLM local."""
    role_name = task.get("role", "")
    payload = task.get("payload", "")
    
    if not role_name or not payload:
        return {"error": "Faltando 'role' ou 'payload'"}
        
    # Tenta ler o arquivo de persona
    # O worker assume que a pasta 'roles' está no mesmo diretório do run_task.py
    # Para o Ultra rodando ele mesmo, pode ser no __file__.parent
    base_dir = os.path.dirname(os.path.abspath(__file__))
    role_path = os.path.join(base_dir, "roles", f"{role_name}.md")
    
    if not os.path.exists(role_path):
        return {"error": f"Persona não encontrada no worker: {role_path}"}
        
    try:
        with open(role_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except Exception as e:
        return {"error": f"Erro lendo persona: {e}"}
        
    # Constrói o histórico para a LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload}
    ]
    
    # Reaproveita a função LLM já existente no worker
    llm_task = {
        "messages": messages,
        "temperature": 0.2
    }
    
    result = await _do_llm_generate(llm_task)
    
    if "result" in result:
        return {"result": result["result"]}
    else:
        return result # Retorna o erro se falhou

async def _do_get_status(task: dict) -> dict:
    import subprocess
    parts = []
    
    # Bateria
    try:
        res = subprocess.run(
            ["termux-battery-status"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            bat = json.loads(res.stdout)
            parts.append(f"Bateria: {bat.get('percentage', '?')}% ({bat.get('status', '?')})")
    except Exception:
        parts.append("Bateria: indisponível")

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

    # RAM
    try:
        res = subprocess.run(
            ["free", "-m"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            lines = res.stdout.strip().split("\n")
            if len(lines) > 1:
                cols = lines[1].split()
                parts.append(f"RAM: {cols[2]}MB usado / {cols[1]}MB total")
    except Exception:
        pass

    # CPU
    try:
        res = subprocess.run(
            ["top", "-n", "1", "-m", "1"], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            import re
            # Procura por linha que tenha '%cpu' (com ou sem caracteres de escape ANSI)
            for line in res.stdout.split('\n'):
                # Strip ANSI escape codes
                clean_line = re.sub(r'\x1b\[[0-9;]*[mGKFnHJsu]', '', line)
                if 'cpu' in clean_line.lower() and 'user' in clean_line.lower():
                    # Pega a linha limpa
                    parts.append(f"CPU: {clean_line.strip()}")
                    break
    except Exception:
        pass
        
    return {"result": "\n  ".join(parts)}


async def _do_search(task: dict) -> dict:
    """Busca web usando keys locais do worker."""
    try:
        # Importa web_search local (deve estar na pasta do worker)
        sys.path.insert(0, os.path.expanduser("~/IaraWorker"))
        import web_search

        query = task.get("query", "")
        max_results = task.get("max_results", 5)

        result = await web_search.web_search(query, max_results=max_results)
        return {"result": result}
    except Exception as e:
        return {"error": f"Search falhou: {str(e)[:300]}"}


async def _do_deep_read(task: dict) -> dict:
    """Lê URL via Jina Reader usando keys locais."""
    try:
        sys.path.insert(0, os.path.expanduser("~/IaraWorker"))
        import web_search

        url = task.get("url", "")
        content = await web_search.web_read(url)
        return {"result": content}
    except Exception as e:
        return {"error": f"Deep read falhou: {str(e)[:300]}"}


async def _do_llm_generate(task: dict) -> dict:
    """Gera resposta via LLM usando keys locais do worker."""
    try:
        import aiohttp

        messages = task.get("messages", [])
        temperature = task.get("temperature", 0.3)

        # Usar Groq (key local do worker)
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        if not api_key:
            return {"error": "GROQ_API_KEY não configurada neste worker"}

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 4096,
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return {"result": content}
                else:
                    error = await resp.text()
                    return {"error": f"Groq API {resp.status}: {error[:200]}"}

    except Exception as e:
        return {"error": f"LLM generate falhou: {str(e)[:300]}"}


async def main():
    """Lê tarefa do stdin, executa, retorna via stdout."""
    try:
        raw = sys.stdin.read()
        task = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        print(json.dumps({"error": f"JSON inválido: {e}"}))
        sys.exit(1)

    result = await handle_task(task)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
