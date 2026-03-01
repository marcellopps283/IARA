
--- FILE: run_task.py ---
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

--- END FILE ---

--- FILE: network.py ---
import asyncio
import socket
import json
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceInfo
from zeroconf import ServiceBrowser, ServiceStateChange

# --- MÓDULO DE DESCOBERTA mDNS (ZERO_CONF) --- #
SERVICE_TYPE = "_zeroclaw._tcp.local."
MASTER_NAME = "S21_Ultra_Master"
WORKER_PREFIX = "Worker_"

class NetworkController:
    def __init__(self, node_type="master", port=5555):
        self.node_type = node_type
        self.port = port
        self.aio_zc = None
        self.info = None
        self.known_workers = {} # {nome_do_servico: (ip, porta, status)}
        self.loop = asyncio.get_running_loop()

    async def get_local_ip(self):
        """Retorna o IP local na rede Wi-Fi"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Callback acionado quando um nó entra ou sai da rede (roda em thread paralela do zc)"""
        if state_change is ServiceStateChange.Added:
            # Precisa injetar a corrotina de volta no event loop principal
            asyncio.run_coroutine_threadsafe(self.on_service_added(zeroconf, service_type, name), self.loop)
        elif state_change is ServiceStateChange.Removed:
            print(f"Nó Desconectado: {name}")
            if name in self.known_workers:
                del self.known_workers[name]

    async def on_service_added(self, zeroconf, service_type, name):
        """Resolve o endereço de um novo Worker descoberto"""
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)
        
        if info:
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            # Recupera os metadados (TXT records), como temperatura/bateria 
            properties = {k.decode('utf-8'): v.decode('utf-8') for k, v in info.properties.items()}
            print(f"Novo Nó Detectado: {name} em {ip}:{port} - Props: {properties}")
            
            if name.startswith(WORKER_PREFIX):
                self.known_workers[name] = {"ip": ip, "port": port, "props": properties}

    async def start_broadcasting(self, properties=None):
        """Anuncia a própria existência na rede local via mDNS"""
        self.aio_zc = AsyncZeroconf()
        ip = await self.get_local_ip()
        
        if self.node_type == "master":
            name = f"{MASTER_NAME}.{SERVICE_TYPE}"
        else:
            # Em um cenário distribuído real, usaríamos um ID único (MAC address)
            name = f"{WORKER_PREFIX}Local_{self.port}.{SERVICE_TYPE}"

        if properties is None:
            properties = {"status": "online", "type": self.node_type}

        self.info = AsyncServiceInfo(
            SERVICE_TYPE,
            name,
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties=properties
        )
        
        print(f"Broadcasting mDNS {self.node_type.upper()} em {ip}:{self.port} como {name}")
        await self.aio_zc.async_register_service(self.info)

        if self.node_type == "master":
            # O Master atua como um Browser para localizar os Workers
            self.browser = ServiceBrowser(self.aio_zc.zeroconf, SERVICE_TYPE, handlers=[self.on_service_state_change])

    async def shutdown(self):
        """Desliga o broadcast civilizadamente"""
        if self.aio_zc:
            if self.info:
                await self.aio_zc.async_unregister_service(self.info)
            await self.aio_zc.async_close()
            print(f"Broadcast encerrado para {self.node_type}.")

# Exemplo de teste rápido que pode ser acionado apenas importando
async def test_mdns():
    print("Iniciando testes mDNS Locais...")
    master = NetworkController(node_type="master", port=5555)
    worker1 = NetworkController(node_type="worker", port=5556)
    
    await master.start_broadcasting()
    await asyncio.sleep(1) # Aguarda master decolar
    await worker1.start_broadcasting(properties={"battery": "80%", "temp": "35C"})
    
    await asyncio.sleep(3) # Aguarda descoberta preencher o dicionário do Master
    print(f"Workers mapeados pelo Master: {list(master.known_workers.keys())}")
    
    await worker1.shutdown()
    await master.shutdown()

if __name__ == "__main__":
    asyncio.run(test_mdns())

--- END FILE ---

--- FILE: sandbox.py ---
import os
import tempfile
import asyncio
import shutil
import sys
from pathlib import Path

# Pasta permanente de evolução da Kitty
SHADOW_DIR = os.path.expanduser("~/Kitty_Shadow")

async def run_in_sandbox(python_code: str, timeout: int = 15):
    """
    Executa código gerado por IA em um ambiente estéril e efêmero.
    No Android/Termux, usa "proot" para enjaular o sistema de arquivos.
    No Windows de desenvolvimento, usa pastas temporárias isoladas.
    """
    result = None
    try:
        # 1. Cria espaço limpo (Garbage Collection efêmera garantida ao fechar bloco with)
        with tempfile.TemporaryDirectory(prefix="zeroclaw_sandbox_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # 2. Escreve o código suspeito no arquivo temporário
            script_target = temp_path / "sandbox_eval.py"
            with open(script_target, "w", encoding="utf-8") as f:
                f.write(python_code)
            
        # 3. Se houver dependências na Shadow, clona elas SOMENTE para leitura neste temp
        if os.path.exists(SHADOW_DIR):
            for item in os.listdir(SHADOW_DIR):
                src = os.path.join(SHADOW_DIR, item)
                dst = temp_path / item
                if os.path.isfile(src):
                    shutil.copy2(src, dst)

            # 4. Determina o comando do interpretador isolado
            if sys.platform == "win32":
                # No dev cockpit, restringe o diretório de trabalho do processo 
                # (não é um chroot real, mas simula o ambiente de teste)
                cmd = [sys.executable, str(script_target)]
            else:
                # Termux: Invoca PRoot para forçar a raiz simulada e blindar o Android
                # "proot -0 -r {temp_dir} -b /data/data/com.termux/files/usr /usr/bin/python ..."
                # Abaixo é a montagem segura onde o bot pensa que a raiz '/' é o tempfile
                termux_python = shutil.which("python") or "python"
                termux_usr = "/data/data/com.termux/files/usr"
                cmd = [
                    "proot", 
                    "-0", # Fake root
                    "-r", str(temp_path), 
                    "-b", f"{termux_usr}:{termux_usr}", # Leva interpretador junto
                    "-w", "/", # Fixa o dir de trabalho dentro da jaula
                    termux_python, "sandbox_eval.py"
                ]

            try:
                # 5. Execução com Timeout de CPU e captura Assíncrona de I/O
                if sys.platform == "win32":
                    import subprocess
                    def sync_run():
                        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                    try:
                        proc = await asyncio.to_thread(sync_run)
                        process = type('obj', (object,), {'returncode': proc.returncode})
                        out_str = proc.stdout[:10000]
                        err_str = proc.stderr[:10000]
                    except subprocess.TimeoutExpired:
                        raise asyncio.TimeoutError()
                else:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                    out_str = stdout.decode('utf-8', errors='ignore')[:10000] 
                    err_str = stderr.decode('utf-8', errors='ignore')[:10000]

                if process.returncode == 0:
                    result = {"status": "success", "output": out_str.strip()}
                else:
                    result = {"status": "error", "error_type": "Execução Falhou", "traceback": err_str.strip() or out_str.strip()}

            except asyncio.TimeoutError:
                print("Sandbox: OOM/Infinite Loop Evitado. Matando processo.")
                try:
                    if 'process' in locals() and hasattr(process, 'kill'):
                        process.kill()
                        await process.wait()
                except ProcessLookupError:
                    pass
                result = {"status": "error", "error_type": "Timeout Acionado", "traceback": "Processo demorou mais que o limite estabelecido e foi aniquilado sumariamente."}
            except OSError as e:
                # Catch specific runtime OS errors without triggering tempfile handlers
                result = {"status": "error", "error_type": "Erro de I/O do processo", "traceback": str(e)}
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                result = {"status": "error", "error_type": "Erro Ambiental", "traceback": f"{str(e)}\n{tb}"}

    # Tratamento de erro específico do Windows para testes locais da lixeira
    except OSError as e:
        if sys.platform == 'win32':
             if not result:
                 result = {"status": "error", "error_type": "Timeout Acionado", "traceback": f"Processo testado com sucesso mas Lixeira Windows falhou na delecao: {e}"}
        else:
             raise e
    except Exception as e:
        import traceback
        result = {"status": "error", "error_type": "Global Error Trap", "traceback": traceback.format_exc()}

    return result or {"status": "error", "error_type": "Fatal Crash", "traceback": "Processo extinto no nível OS."}

# --- TDD Simples de Sandbox ---
async def test_sandbox():
    print("Testando Execução Normal...")
    code_ok = "print('Sou a Kitty rodando na caixa!')\nx = 2 + 5\nprint(f'Soma {x}')"
    res1 = await run_in_sandbox(code_ok)
    print(res1)
    
    print("\nTestando Timeout/Loop Infinito...")
    code_bad = "while True:\n    pass\n"
    res2 = await run_in_sandbox(code_bad, timeout=2) # 2 segundos paara estourar rápido
    print(res2)

if __name__ == "__main__":
    asyncio.run(test_sandbox())

--- END FILE ---
