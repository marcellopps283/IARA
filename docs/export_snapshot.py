import os
import re

def sanitize(content):
    content = re.sub(r'([A-Za-z0-9_]*API_KEY\s*=\s*)(["\'].*?["\'])', r'\1"__REDACTED__"', content)
    content = re.sub(r'([A-Za-z0-9_]*TOKEN\s*=\s*)(["\'].*?["\'])', r'\1"__REDACTED__"', content)
    content = re.sub(r'os\.getenv\(["\'](.*?API_KEY|.*TOKEN)["\'],\s*["\'].*?["\']\)', r'os.getenv("\1", "__REDACTED__")', content)
    
    # Mascarar qualquer email que pareça estar no código
    content = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r'__REDACTED_EMAIL__', content)
    return content

def write_snapshot(filename, chunks):
    path = os.path.join(r"c:\Users\marce\Desktop\projetin\docs", filename)
    with open(path, "w", encoding="utf-8") as f:
        for fname, text in chunks:
            f.write(f"\n--- FILE: {fname} ---\n")
            f.write(text)
            f.write(f"\n--- END FILE ---\n")

# A (Overview)
overview = """# Exportação de Projeto - Visão Geral do Sistema Swarm Iara

O que o sistema faz:
A Iara/ZeroClaw é um sistema multiagente que gerencia LLMs via Nuvem processando de dentro de aparelhos Android (Termux) e Windows. O sistema é baseado em um Master (Orquestrador) e em subredes de controle conhecidas como Workers. Ele lida autonomamente com pesquisas extensas na internet, console administrativo e execução de sandbox de código Python na máquina Host, roteando chamadas entre Llama 3 (Groq/Cerebras) e Kimi K2.5 baseado nos limites das APIs. Possui resiliência contra quebras, limitadores de concorrência global de tráfego, persistência de banco de dados SQLite para prevenir amnésia crônica em crashes de kernel (Doze Mode).

Como rodar:
O módulo principal (Master) no S21 Ultra deve ser rodado com `python brain.py`. A interface WEB FastAPI para o painel se levanta passivamente em `python dashboard_api.py`.
O módulo Secundário (Worker) nos celulares subsidiários (FE/Secundários) iniciam individualmente com input loop usando o script `python run_task.py`. Toda conexão é enviada via SSH. 

Quais agentes existem e papéis:
- Iara Master (Cérebro Principal, Gerencia Telegram, Planeja pesquisa, delega threads).
- Pesquisador (Executa o deep_research buscando em paralelo).
- Revisor (Valida dados coletados dos Workers).

Tools implementadas:
`search_web`, `read_web`, `read_document` (PDF, DOCX, CSV), `get_location`, `get_bateria`, `turn_on_flashlight`, e delegação assíncrona SSH `swarm_task`.

Loop de Execução:
O Input contínuo é via Polling de Bot do Telegram (aiogram) ou via Dashboard Web (SSE FastApi) no Master. Mensagens ativam ferramentas no loop de tool calls baseada no framework nativo OpenAI/Aiohttp. Quando requer capacidade extrema, usa-se a keyword "swarm" repassando um payload encapsulado no `orchestrator.py` para injetar SSH sobre o nó menos carregado da rede detectado pelo mDNS (`network.py`).

Estado:
- DB relacional local `kitty_memory.db` com separação de Memória RAM Volátil (Conversacional de curto termo), Memória Episódica, Fatos Perenes Consolidados a cada Madrugada pelo loop autônomo. Fila persistida do Swarm na tabela `swarm_jobs`.
"""

# B (Directory)
b_content = """# Estrutura do Repositório (Depth 2 e Arquivos Essenciais)

root/
- .agents/
- dashboard/
  - index.html
- docs/
- identity/
  - kitty_instructions.md
- roles/
  - pesquisador.md
  - revisor.md
- skills/
- brain.py (Ponto de entrada Assíncrono para o Master Iara no celular principal)
- core.py (Gerenciador SQL Persistente de Memórias, Lembretes e Jobs)
- config.py (Variáveis globais, limites de falha e tokens REDACTEDS)
- orchestrator.py (Scheduler assíncrono e balanceador Swarm)
- worker_protocol.py (Criação Subprocess e Pipes SSH para Workers)
- llm_router.py (Sistema LLM Agnostic de envio à OpenAI API Models, Fallbacks para Rate limit HTTP 429)
- run_task.py (Ciclo assíncrono Worker-Side local que ouve a porta stdin e dispara output stdout)
- network.py (Implementação experimental Zeoconf mDNS para auto-descobrir androids na rede)
- sandbox.py (Runtime PRoot isolador e chroot para códigos arbitrários executados pela Web)
- deep_research.py (Lógica Plan & Execute distribuída)
- doc_reader.py (Integra PDFPlumber e Docx para leitura crua de anexos locais)
- telegram_bot.py (Frontend aiogram para mensagens interativas com Markdown Stream)
- dashboard_api.py (Web Interface SSE de Streaming de mensagens sem block)
"""

base = r"c:/Users/marce/Desktop/projetin"
def get_file(rel):
    try:
        with open(os.path.join(base, rel), "r", encoding="utf-8") as f:
            return sanitize(f.read())
    except Exception as e:
        return f"[Arquivo não encontrado: {e}]"

os.makedirs(os.path.join(base, "docs"), exist_ok=True)

with open(os.path.join(base, "docs", "SNAPSHOT_01_A_VisaoGeral.md"), "w", encoding="utf-8") as f:
    f.write(overview)

with open(os.path.join(base, "docs", "SNAPSHOT_02_B_Estrutura.md"), "w", encoding="utf-8") as f:
    f.write(b_content)

write_snapshot("SNAPSHOT_03_C_Master_Core.md", [
    ("brain.py", get_file("brain.py")),
    ("core.py", get_file("core.py")),
    ("config.py", get_file("config.py"))
])

write_snapshot("SNAPSHOT_04_C_Swarm_Balance.md", [
    ("orchestrator.py", get_file("orchestrator.py")),
    ("worker_protocol.py", get_file("worker_protocol.py")),
    ("llm_router.py", get_file("llm_router.py"))
])

write_snapshot("SNAPSHOT_05_C_Workers.md", [
    ("run_task.py", get_file("run_task.py")),
    ("network.py", get_file("network.py")),
    ("sandbox.py", get_file("sandbox.py"))
])

write_snapshot("SNAPSHOT_06_C_Skills.md", [
    ("deep_research.py", get_file("deep_research.py")),
    ("doc_reader.py", get_file("doc_reader.py")),
    ("web_search.py", get_file("web_search.py"))
])

write_snapshot("SNAPSHOT_07_C_Interface.md", [
    ("telegram_bot.py", get_file("telegram_bot.py")),
    ("dashboard_api.py", get_file("dashboard_api.py")),
    ("dashboard/index.html", get_file("dashboard/index.html"))
])

write_snapshot("SNAPSHOT_08_C_Personas.md", [
    ("identity/kitty_instructions.md", get_file("identity/kitty_instructions.md")),
    ("roles/pesquisador.md", get_file("roles/pesquisador.md")),
    ("roles/revisor.md", get_file("roles/revisor.md"))
])
print("SNAPSHOTS WRITTEN SUCCESSFULLY")
