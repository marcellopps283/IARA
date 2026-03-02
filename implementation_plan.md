# IARA v3 — Arquitetura de Colmeia Distribuída (NOVORUMO)

Este documento mapeia o curso da "Fase V3", integrando uma Malha de Conexão Distribuída entre o Console da IARA e workers Android externos.

## User Review Required 

**Todos os fluxos foram estabilizados e aprovados pelo usuário.** O planejamento está tecnicamente encerrado e as diretrizes arquiteturais para resiliência distribuída foram preenchidas, tampando as lacunas de Visibilidade de Debug, Limites de Custo e IP Dinâmico do VPN.

## Proposed Changes: Fases Adicionais (Ordem de Execução)

### FASE 7: Esqueleto Visual SSE, Quota Diária e HITL Policy (As Lentes do Debug)
- **Modificações (SSE Skeleton)**: `dashboard_api.py` e Frontend React.
- Mover a construção do Backend Streamer pro momento M-0. Implementar o endpoint nativo via SSE Yieldings, exibindo um log console temporário limpo em tempo real no Site (`STATUS: Convocando Conselho`, `THINKING...`) para guiar a visualização remota dos passos seguintes sem cegar o desenvolvedor.
- **Modificações (Quotas Preventivas)**: `config.py` e `llm_router.py`. Adição da chave `MAX_DAILY_LLM_CALLS = 150`. Barreira nativa antes do dispare paralêlo do `gather` no caso de Conselho ou Loops de Auto_Reflection agressivos.
- **Preparativo (HITL)**: Instanciaremos o `IARA_HITL_POLICY.md` definindo limites textuais de Ações Seguras / Médias / Críticas antes de programar as suspensões da IARA e do Suborno do Conselho.

### FASE 8: Roteamento Inteligente (Econômico vs Qualidade)
- **Modificações**: `brain.py` e `llm_router.py`.
- **Rápido**: Uso intensivo de provedores ultrarrápidos via flag `require_fast=True`
- **Escalation Automático (R1)**: A IARA ganhou autonomia. Se a camada Groq der Timeout/Falhar duas vezes, ou se a conversa demandar complexidade extrema, abandona a camada rasteira e engaja o DeepSeek R1 no OpenRouter ativamente.

### FASE 9: Conexão Neural Dinâmica (Tailscale VPN) & Resiliência
- **Modificações**: `config.py`, `worker_protocol.py`, API Caller.
- **Ping Tailscale Dinâmico**: Ao invés de hardcodarmos `100.x.x.x` cego, acoplaremos uma requisição HTTP REST na inicialização da rede buscando a lista da malha (Tailnet) que aponta as chaves estáticas pro MAC adress do S21 FE via `/api/v2/tailnet/-/devices`. Retornará pro `env` injetando IP sempre certeiro, isentando configurações manuais a cada Reset.
- **Transporte Físico (SCP)**: Tarefas analíticas exigindo parsing físico despacharão arquivos `scp -P 2022 arquivo target@$DYNAMIC_IP`.
- **Recuperação de Hardware Amnesia**: Polling ativo em sub-trabalhadores recuperará respostas se o Master S21 Ultra for morto pelo Android OOM killer no meio da análise de dados de 15 minutos do feixe escravo.
- **Kill Switch Integral**: CancellationToken backend propagará `ssh pkill -f` limpando completamente tarefas remanescentes no FE quando estouradas pelo Board UI.

### FASE 10: Conselho Limitado (Presidente + Red vs Blue Team)
- **Modificações**: `pipeline.py` e `orchestrator.py`.
- Nova intenção: "council", onde chamamos `asyncio.gather`.
- **Human Inversion**: Limite preventivo. Presidente com 3 chances para o consenso de projeto. Red Team vs Blue Team com 2 tentativas de escrita de arquivos antes da IARA parar ativamente e clamar aprovação/correção do Telegram com base nos Níveis High Risk da Policy HITL recém gerada.

### FASE 11: Extensão de Nuvem e Código Híbrido (WASM/E2B)
- **Modificações**: `tools/e2b_tool.py`, `sandbox.py` local.
- Híbrido ativado: Tarefas massivas de machine learning forçam envio ao `E2B SDK`. Tarefas limpas nativas permanecem no Pyodide/Proot local.

### FASE 12: Memória Multi-Projetos (Embeddings Vectors e React Base Selectors)
- **Modificações (Full Stack)**: `core.py`, `brain.py`, Componentes Frontend React.
- Particionamento FTS5/Cohere API no `core.py`.
- **Injeção UI Activa**: Desenvolvimento de novo componente `<Select Dropdown>` no front-end listando instâncias obtidas do `/api/projects`. Toda chamada SSE ao chat herdará a Key do projeto nativamente.

## Verification Plan

### Testes Automáticos
- Disparar requisições contínuas simuladas para violar a trave de segurança da `Quotas (Rate Limiter)` e atestar o desligamento gentil limitando budget diário de Tokens.
- Validar se APIs públicas do Tailscale respondem localmente de forma agnóstica sem interceptação da Rede 4G.
