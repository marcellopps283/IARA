# IARA v3 — Arquitetura de Colmeia Distribuída (NOVORUMO)

Este documento mapeia o curso da "Fase V3", integrando uma Malha de Conexão Distribuída entre o Console da IARA e workers Android externos.

## User Review Required 

**Todos os fluxos foram estabilizados e aprovados pelo usuário.** O planejamento está tecnicamente encerrado e as diretrizes arquiteturais para resiliência distribuída foram preenchidas, tampando as lacunas de Visibilidade de Debug, Limites de Custo e IP Dinâmico do VPN.

## Proposed Changes: Fases Adicionais (Ordem de Execução)

### FASE 7: Esqueleto Visual SSE, Quota Diária e HITL Policy (As Lentes do Debug)
- **Modificações (SSE Skeleton)**: `dashboard_api.py` e Frontend React.
- Mover a construção do Backend Streamer pro momento M-0. Implementar o endpoint nativo via SSE Yieldings, acompanhado apenas de um componente React temporário. *O frontend nesta fase atuará puramente como um console de linha de comando reativo mostrando o `STATUS: Convocando Conselho`, `THINKING...`, para guiar a visualização remota sem precisarmos da UI bonita da Fase 12 ainda.*
- **Modificações (Quotas Preventivas)**: `config.py` e `llm_router.py`. Adição da chave `MAX_DAILY_LLM_CALLS = 150`. Barreira nativa antes do dispare paralêlo do `gather` no caso de Conselho ou Loops de Auto_Reflection agressivos.
- **Preparativo (HITL)**: Instanciaremos o `IARA_HITL_POLICY.md` definindo limites textuais de Ações Seguras / Médias / Críticas antes de programar as suspensões da IARA e do Suborno do Conselho (Fase 10).

### FASE 8: Roteamento Inteligente (Econômico vs Qualidade)
- **Modificações**: `brain.py` e `llm_router.py`.
- **Rápido**: Uso intensivo de provedores ultrarrápidos via flag `require_fast=True`
- **Escalation Automático (R1)**: A IARA será promovida. Ocorre ativado pelas duas chaves ativas simultaneamente: se a camada Groq der Timeout/Falhar duas vezes (Motivo Técnico) OU se a conversa possuir verbos que exijam complexidade semântica explícita (Motivo Intelectual), abandona a camada rasteira e engaja o DeepSeek R1 no OpenRouter ativamente.

### FASE 9: Conexão Neural Dinâmica (Tailscale VPN) & Resiliência
- **Modificações**: `config.py`, `worker_protocol.py`, API Caller.
- **Teste Empírico de Descoberta**: Antes do Agent escrever o protocolo, geraremos um minisscript Ping Test. Esse script irá recuperar dinamicamente o IP pela API (`/api/v2/tailnet/-/devices`) e tentar pingar a rota SSH do S21 FE isoladamente. Apenas mediante esse ping pass-tru, implementamos o Bind no código final.
- **Transporte Físico (SCP)**: Tarefas analíticas exigindo parsing físico despacharão arquivos `scp -P 2022 arquivo target@$DYNAMIC_IP`.
- **Recuperação de Hardware Amnesia**: Polling ativo em sub-trabalhadores recuperará respostas se o Master S21 Ultra for morto pelo Android OOM killer no meio da análise de dados de 15 minutos do feixe escravo.
- **Kill Switch Integral**: CancellationToken backend propagará `ssh pkill -f` limpando completamente tarefas remanescentes no FE quando estouradas pelo Board UI.

### FASE 10: Conselho Limitado (Presidente + Red vs Blue Team)
- **Modificações**: `pipeline.py` e `orchestrator.py`.
- Nova intenção: "council", onde chamamos `asyncio.gather`.
- **Human Inversion**: Limite preventivo. Presidente com 3 chances para o consenso de projeto. Red Team vs Blue Team com 2 tentativas de escrita de arquivos antes da IARA parar ativamente e clamar aprovação/correção do Telegram com base nos Níveis High Risk da Policy HITL gerada.

### FASE 11: Extensão de Nuvem e Código Híbrido (WASM/E2B)
- **Modificações**: Criar `skills/e2b_sandbox_skill.py`, atualizar `requirements.txt`.
- Híbrido ativado: Tarefas massivas de machine learning ou alto risco forçam envio para o `E2B SDK`. Tarefas limpas nativas permanecem no Proot local via Shadow_Skill.
- **Integração E2B Code Interpreter**: A skill iniciará uma Sandbox efêmera na nuvem (`e2b_code_interpreter`), enviará o código contendo processamento pesado (pandas/matplotlib).
- **Extração Cloud (Base64)**: Capturar os artefatos visuais plotados (`results[0].png` ou `base64`), embutir numa string contendo a imagem em base64 e retornar. Assim, o backend repassará a imagem gerada na nuvem via SSE Stream direto pro Dashboard Web.

### FASE 12: Memória Contextual Orientada a Objeto (Full Stack Projects)
Esta fase adota a estratégia "Isolation First, Semantic RAG Second".

**Etapa 1: Project Isolation (Isolamento Lógico)**
- **Modificações (DB Schema)**: `core.py`
  - Criar tabela `projects` (id, name, description, created_at).
  - Criar tabela `app_config` (key, value) para armazenar `active_project_id`.
  - Adicionar coluna `project_id (DEFAULT NULL)` nas tabelas `history` (working_memory), `core_memory` e `episodic_memory`. 
    - *Atenção (Migração)*: `NULL` será tratado como o "Escopo Global". Qualquer histórico legado pertencerá nativamente ao global.
- **Modificações (Backend Logic - core.py Refatoração Massiva)**:
  - `save_message()`: Adicionar `project_id`.
  - `get_conversation()`: `WHERE project_id = ? OR project_id IS NULL`.
  - `save_core_fact()`: Adicionar `project_id`.
  - `get_core_memory()`: Filtrar por projeto.
  - `compact_working_memory()`: Propagar `project_id` na sumariação do episódio.
  - `save_episode()`: Adicionar `project_id`.
- **Modificações (Backend Logic - Rotas e Controllers)**: `brain.py`, `dashboard_api.py`, `telegram_bot.py`
  - `brain.py`: Ler `active_project_id` da `app_config` no início de `process_message()`. Isso sincroniza Telegram e React no mesmo escopo ativo da memória.
  - `telegram_bot.py`: Criar handler `/projeto [nome]` que cria/seta o escopo na Tabela `app_config`.
  - `dashboard_api.py`: Expor `GET /api/projects` e `POST /api/projects/activate/{id}` atualizando `app_config`.
- **Modificações (Frontend React)**: 
  - Adicionar Dropdown `<ProjectSelector>` no Header chamando o endpoint de ativação. Isso garante que a UI comande e reflita a mesma Engine de Estado (`app_config`) lida pela IARA.

**Etapa 2: Semantic RAG (Embeddings Assíncronos no Alvo Certo)**
- **Geração (Background)**: Ao salvar dados na `core_memory` e na `episodic_memory`, gerar embeddings via **Cohere** (`cohere.Client`) de forma **assíncrona** (`asyncio.create_task`) para não onerar o loop de conversa. Salvar como BLOB. A `working_memory` NÃO receberá embeddings pois já é lida em RAW text via Context Window.
- **Recuperação (RAG)**: Ao processar nova mensagem (no início de `process_message()`), usar a API Cohere para gerar o **embedding da query do usuário** em tempo real. Passar essa query embeddada (junto do texto) para a `build_system_prompt()`. Dentro dela, fazer Cosine Similarity no Python (sobre a `episodic_memory` e `core_memory` **filtradas** pelo `project_id`) e injetar apenas os TOP-3 episódios e top fatos no prompt. Redução drástica de latência de chamadas!

## Verification Plan

### Testes Automáticos
- Disparar requisições contínuas simuladas para violar a trave de segurança da `Quotas (Rate Limiter)` e atestar o desligamento gentil limitando budget diário de Tokens.
- Validar se APIs públicas do Tailscale respondem localmente de forma agnóstica sem interceptação da Rede 4G rodando o Ping Script da Fase 9.

### FASE 13: Function Calling (Tool Use Formal)
O objetivo desta fase é abandonar as frágeis listas de keywords na detecção de "intent" e abraçar o uso nativo de *Function Calling* (modelo OpenAI-compatible) para rotear intents, mantendo o fallback resiliente para as keywords legadas em provedores menos granulares.

**1. Centralização (tools_registry.py)**
- Criar o arquivo `tools_registry.py` contendo a lista unificada de schemas JSON para todas as funções (`web_search`, `deep_research`, `save_memory`, `recall_memory`, `get_weather`, `get_system_status`, `set_reminder`, `toggle_flashlight`, `get_location`, `read_url`, `run_sandbox`, `swarm_delegate`, `deep_research_council`).

**2. Preparação do LLM Router (llm_router.py)**
- Adaptar o `LLMRouter.generate()` para aceitar o kwarg estrito `tools`.
- Quando um provedor sinalizar *tool_calls* via `finish_reason`, mapear e extrair o `name` e processar a desserialização do JSON de `arguments`, retornando padronizado como `{"tool": nome, "args": {...}}`.
- Provedores incompatíveis com Function Calling (Ex: Cerebras) irão naturalmente ignorar este array.

**3. Inteligência Híbrida (brain.py)**
- Criar nova pipe principal `classify_intent_with_tools(text, router)` invocando `router.generate` sob *require_fast=True*.
- Tratar o dict gerado e rotear na mesma estrutura legada `("intent", query)` que já alimenta `execute_tools()`.
- **Mapeamento Crítico (Tool → Intent)**: Como `execute_tools()` espera uma tupla legada, será implementado o seguinte conversor:
  - `web_search`          → `("search",   args["query"])`
  - `deep_research`       → `("deep_research", args["query"])`
  - `save_memory`         → `("save_memory",   args["content"])`
  - `recall_memory`       → `("recall_memory", None)`
  - `get_weather`         → `("weather",  None)`
  - `get_system_status`   → `("status",   None)`
  - `set_reminder`        → `("reminder", args["message"] + " " + args["time_expression"])`
  - `toggle_flashlight`   → `("flashlight", args["state"])`
  - `get_location`        → `("location", None)`
  - `read_url`            → `("url_read", args["url"])`
  - `run_sandbox`         → `("sandbox",  args["task_description"])`
  - `swarm_delegate`      → `("swarm",    args["task"])`
  - `deep_research_council` → `("council", args["query"])`
- Criar rotina formal de *Try/Except* que degrada a leitura para a função purista velha de `classify_intent()` garantindo retrocompatibilidade 100%.
- Adicionar no bloco de comandos especiais o `/tools`, permitindo ver as descrições em tela do *tools_registry*.
