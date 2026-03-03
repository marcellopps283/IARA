# I.A.R.A — Plano de Implementação v2 (Arquitetura Agentic)

## Fase 0: Fundação ✅
- [x] Otimização e reestruturação da base (brain, orchestrator, deep_research)
- [x] Frontend Web UI (React + Vite + shadcn) PWA com suporte iOS
- [x] Integrações nativas PWA e Backup automático Google Drive SQLite

## Fase 1: Governança e Máquina de Estado (TodoWrite & Message Channels) ✅
- [x] **Message Channels no `brain.py` e Telegram**:
  - [x] Implementar sistema de mensagens interno invisível (`analysis`).
  - [x] Implementar canal de interface de progresso (`commentary`).
  - [x] Implementar envio de confirmações e dumps finais (`final`).
- [x] **Stateful Todo Machine (`orchestrator.py`)**:
  - [x] Tabela no SQLite `tasks_state` (`pending` -> `in_progress` -> `completed`).
  - [x] Trava de fluxo: Proibir >1 tarefa `in_progress` simultaneamente através do handler `/task start`.
- [x] **PlanMode Lock**:
  - [x] Comando `/plan on` e `/plan off` criados e integrados.

## Fase 2: Injeção de Memória Semântica Avançada (4 Camadas) ✅
- [x] **Extração das Camadas do SQLite para injetar no Prompt**: Metadata, Preferências, Tópicos Ativos e Retomada Densa concluídos.

## Fase 3: Roteamento Distribuído e Pipeline de 5 Fases ✅
- [x] Acoplar providers com fallback estruturado `task_type` (`chat`, `intent`, `tools`, `reasoning`, `research`, `consolidation`, `code`).

## Fase 4: Especialização Cérebro Coletivo (Pipeline 5 Estágios) ✅
- [x] Criar `pipeline.py` isolando: RESEARCH, PLAN, IMPLEMENT, REVIEW e VERIFY.

## Fase 5: Ecossistema de Eventos e Evolução (Hooks) ✅
- [x] Criar módulo `hooks.py` com pre-compact, SessionEndHook pra aprendizado de base.

## Fase 6: Defesa e Auditoria (Red/Blue Team) ✅
- [x] Hook rigoroso anti-exfiltração resolvendo vazamentos de API keys na resposta LLM.

# NOVORUMO: Evolução V3 (A partir daqui)

## Fase 7: Visual Feedback (SSE Skeleton), Quota Limits & HITL Policy
- [x] **Esqueleto SSE**: Implementar base do FastAPI Server-Sent Events e refatorar React para escutar os yields (STATUS, THINKING, ANSWER) em formato debug textual estrito. Componentes bonitos renderizadores são atrasados pra UI final da Fase 12.
- [x] **Polícia de Cotas (Rate Limiter)**: Adicionar limite preventivo `MAX_DAILY_LLM_CALLS = 150` no `config.py` e barrar no nível do `llm_router.py` antes de arruinar o orçamento.
- [x] **Criação do Documento HITL**: Escrever formalmente o `IARA_HITL_POLICY.md` com 3 Níveis (Safe/Medium/High) para balizar matematicamente os disparos de aprovação do Telegram pro Conselho.

## Fase 8: Roteamento Escalável e Contexto Econômico (Fast vs Heavy)
- [x] Atualizar `classify_intent` para repassar `require_fast=True` ao router em chats normais.
- [x] Rotear requisições fast pro Groq. Escalation Trigger: Ativar fallback pra modelos Reasoning (OpenRouter/R1) se timeout/failure no Groq bater 2 tentativas consecutivas OU intenção semântica forçalada por termos complexos for injetada no Prompt Mestre.

## Fase 9: Automação VPN Tailscale + Recuperação de Falhas
- [x] **Descoberta Dinâmica de IP**: Criar script inicial para bater na API Rest do Tailscale devolvendo o IP `100.x` do Worker usando hostname constante.
- [x] **Integração no Protocolo**: Conectar o script de descoberta ao `worker_protocol.py` da IARA para que, em caso de erro, ao invés de desistir, tente se reconectar ao Tailscale do Moto G4 ou S21 FE antes de fail.
- [x] **ZeroMQ Heartbeat**: Implementar envio explícito de ping no `transport.py` do Worker pra manter a comunicação TCP resiliente caso o Wi-Fi do host pisque.
- [x] **Redundância Híbrida**: Adicionar File Transfer físico (SCP) ao wrapper de conexão SSH no `worker_protocol.py`.
- [x] **Recuperação de Amnésia**: Master lê `in_progress` da DB ao resetar via polling no `on_session_start` caçando tarefas órfãs abandonadas no S21.
- [x] Kill Switch remetente: `/api/kill` propaga cancelamentos pro Android Escravo.

## Fase 10: Conselho Expandido (Blue/Red Team Distribuídos)
- [x] Nova intenção `council` disparando `asyncio.gather` em provedores multi-modal (Groq, Cerebras, Mistral) consolidando com modelo Presidente.
- [x] Lock do Conselho a 3 tentativas, balizado pelo `IARA_HITL_POLICY.md`.
- [x] Lock do Blue Team S21 FE rejeitando perigos de sistema, com bail-out após 2 tentativas pro Telegram.

## Fase 11: Sandbox Absoluta (Decision WASM vs E2B Híbrida)
- [x] Integrar extensão remota de nuvem robusta através da API E2B SDK.
- [x] Abordagem Mista confirmada: Execuções nativas WASM ou Python puristas rodam na localidade; E2B isola workloads que drenam ciclos do hardware (Carga + ML).
- [x] **Pipeline de Entrega**: Extrair arquivos e charts contidos no Cloud do E2B fazendo a descida local para o frontend SSE servir os buffers através da UI.

## Fase 12: Memória Contextual Orientada a Objeto (Full Stack Projects)
- [x] **Etapa 1: Project Isolation**
  - [x] DB (core.py): Criar tabelas `projects` e `app_config` (`active_project_id`).
  - [x] DB (core.py): Adicionar coluna `project_id DEFAULT NULL` nas tabelas `history`, `core_memory`, `episodic_memory`. (NULL = Escopo Global).
  - [x] Core (`brain.py`): Ler `active_project_id` em `process_message()`.
  - [x] Core (`core.py` Refactor Massivo): Alterar `save_message`, `get_conversation`, `save_core_fact`, `get_core_memory`, `compact_working_memory` e `save_episode` para injetar/filtrar o `project_id`.
  - [x] Telegram: Handler `/projeto [nome]` para criar/ativar escopos e gravar na `app_config`.
  - [x] Web: Endpoints `GET /api/projects` e `POST /api/projects/activate/{id}`.
  - [x] Web: Componente `<ProjectSelector>` no React Dashboard.
- [x] **Etapa 2: Semantic RAG**
  - [x] Embeddings: Geração Cohere assíncrona guardando BLOB nas tabelas `core_memory` e `episodic_memory`.
  - [x] RAG: Cosine Similarity sobre `episodic_memory` filtrada, limitando a injeção ao TOP-3 episódios no prompt de sistema.

## Fase 13: Function Calling (Tool Use Formal)
- [x] **Etapa 1: Tool Registry Centralizado**
  - [x] Criar arquivo `tools_registry.py` formalizando schemas JSON (OpenAI format) para 13 tools nativas.
- [x] **Etapa 2: LLM Router Refactor**
  - [x] Habilitar kwargs `{tools, tool_choice}` no dispatcher `router.generate()`.
  - [x] Parsear field `tool_calls` quando injetado pelo provider, retornando mapping simples.
- [x] **Etapa 3: Integração Híbrida no Brain**
  - [x] Desenvolver `classify_intent_with_tools` chamando modelo rápido (`require_fast=True`).
  - [x] Implementar Sandbox Try/Except forçando callback p/ regex legado de keywords se houver falha de provider.
  - [x] Integrar handler `/tools` listando catálogo online.

## Fase 14: Agência Autônoma (Background Scheduler)
- [ ] **Etapa 1: Persistência de Jobs (Migration)**
  - [ ] Implementar `scheduled_jobs` no `core.py` (id, name, cron, action, params, enabled, last_run).
  - [ ] Criar CRUD (`add_scheduled_job`, `get_all`, `toggle_job`, etc).
- [ ] **Etapa 2: Motor de Agendamento (scheduler.py)**
  - [ ] Criar loop assíncrono isolado a cada 60 segundos com parsing de `HH:MM` e `interval:Nm`.
  - [ ] Implementar Actions executor: `morning_briefing`, `session_end_hook`, `memory_consolidation`, `custom_search`.
- [ ] **Etapa 3: Interface Proativa (brain.py)**
  - [ ] Injetar `asyncio.create_task(scheduler.start_scheduler())` no main de comunicação (telegram bot startup).
  - [ ] Implementar comandos de terminal em `process_message`: `/cron list`, `/cron add`, `/cron toggle`, `/cron remove`, `/cron run`.
  - [ ] Popular banco virgem com `morning_briefing` (08:00) e `session_end_hook` (23:30) desativados.
