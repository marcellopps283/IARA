# IARA v3 — Arquitetura de Colmeia Distribuída (NOVORUMO)

Este documento mapeia o curso da "Fase V3", integrando uma Malha de Conexão Distribuída entre o Console da IARA e workers Android externos.

## User Review Required 

**Todos os fluxos foram estabilizados e aprovados pelo usuário.** O planejamento está tecnicamente encerrado e as diretrizes arquiteturais para resiliência distribuída foram preenchidas.

## Proposed Changes: Fases Adicionais (Ordem de Execução)

### FASE 7: Roteamento Inteligente (Econômico vs Qualidade)
- **Modificações**: `brain.py` e `llm_router.py`.
- **Rápido**: Uso intensivo de provedores de latência ultrabaixa (Groq/Cerebras) para Intents básicos ("chat", "search") interceptados via flag `require_fast=True`
- **Escalation Automático (R1)**: A IARA ganhou autonomia. Se a camada Groq der Timeout/Falhar duas vezes, ou se a conversa demandar complexidade extrema (ex: word "Aprofunde"), abandona a camada rasteira e engaja o DeepSeek R1 no OpenRouter, devolvendo a latência pro dashboard, consumindo mais contexto ativamente.

### FASE 8: Conexão Neural (Tailscale SSH/SCP) & Resiliência
- **Modificações**: `config.py`, `worker_protocol.py`, `hooks.py`.
- **Teste Empírico Fundamental**: Um script de simulação limpa para tentar "Pingar e autenticar via SSH" o dispositivo S21 FE através da interface TUN 100.x.x.x Tailscale antes do bind Swarm definitivo.
- **Transporte Físico (SCP)**: Em tarefas analíticas que exigem parsing, arquivos acima de megabytes contêm o comando autônomo de subida `scp -P 2022 arquivo target@100.x` para isolar no worker.
- **Recuperação de Hardware Amnesia (Polling de Sobrevivência)**: Quando o Termux do S21 Ultra for morto pelo OOM killer do Android e reiniciar nativamente, a IARA executará um Poll ao Sub-Worker para ler a fila das tarefas órfãs que podem ter sido completadas enquanto ela esteve apagada, evitando refazer análises demoradas.
- **Kill Switch Integral**: CancellationToken backend propagará `ssh pkill -f` via Tailscale no S21 FE matando subprocessos órfãos quando cancelado pelo UI.

### FASE 9: Conselho Limitado (Presidente + Red vs Blue Team)
- **Modificações**: `pipeline.py` e `orchestrator.py`.
- Nova intenção: "council", onde chamamos `asyncio.gather` disparando a mesma instrução pra 3 providers.
- **Human Inversion (3 Strikes)**: O 4° modelo (Presidente) tenta refinar. Se debater em ciclos excedendo 3 tentativas sem encontrar coesão ou segurança na proposta, apita pro Telegram clamando autoridade humana. O mesmo vale pro S21 FE vetar 2 vezes os scripts da Fase de Implementação do Master.

### FASE 10: Extensão de Nuvem e Código Híbrido (WASM/E2B)
- **Modificações**: `tools/e2b_tool.py`, `sandbox.py` local.
- Híbrido ativado: Tarefas massivas de machine learning, OCR de PDFs absurdos ou Matplotlib Arrays gigantes forçam envio ao `E2B SDK`. Tarefas limpas nativas permanecem no Pyodide/Proot local.

### FASE 11: Memória Multi-Projetos (Embeddings Vectors)
- **Modificações**: `core.py`, `brain.py`.
- Particionamento FTS5/Cohere API no `core.py` criando "Pastas/Contextos" mentais isolados na interface baseados no `project_id`.

### FASE 12: O Centro de Comando Visual (SSE Streaming Web)
- **Modificações**: `dashboard_api.py`, Frontend React.
- **Em Segundo Plano**: Acoplaremos o Server-Sent Event feed Stream apenas depois de garantir a estabilidade da orquestração neural.

## Verification Plan

### Testes Automáticos
- `VPN Diagnosis Script`: Um script utilitário garantindo comunicação SSH Tailscale transparente. 
- O simulador Blue Team testará interrupções injetadas deliberadamente durante processamento de arrays propostos pelo Master.
