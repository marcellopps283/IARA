# Exportação de Projeto - Visão Geral do Sistema Swarm Iara

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
