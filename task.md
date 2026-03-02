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
- [ ] **Esqueleto SSE**: Implementar base do FastAPI Server-Sent Events e refatorar React para escutar os yields (STATUS, THINKING, ANSWER) em formato debug textual estrito. Componentes bonitos renderizadores são atrasados pra UI final da Fase 12.
- [ ] **Polícia de Cotas (Rate Limiter)**: Adicionar limite preventivo `MAX_DAILY_LLM_CALLS = 150` no `config.py` e barrar no nível do `llm_router.py` antes de arruinar o orçamento.
- [ ] **Criação do Documento HITL**: Escrever formalmente o `IARA_HITL_POLICY.md` com 3 Níveis (Safe/Medium/High) para balizar matematicamente os disparos de aprovação do Telegram pro Conselho.

## Fase 8: Roteamento Escalável e Contexto Econômico (Fast vs Heavy)
- [ ] Atualizar `classify_intent` para repassar `require_fast=True` ao router em chats normais.
- [ ] Rotear requisições fast pro Groq.
- [ ] Escalation Trigger: Ativar fallback pra modelos Reasoning (OpenRouter/R1) se timeout/failure no Groq bater 2 tentativas consecutivas OU intenção semântica forçalada por termos complexos for injetada no Prompt Mestre.

## Fase 9: Automação VPN Tailscale + Recuperação de Falhas
- [ ] **Descoberta Dinâmica de IP**: Criar script inicial para bater na API Rest do Tailscale devolvendo o IP `100.x` do Worker usando hostname constante.
- [ ] **Teste Inicial de Conexão Obrigatório**: Ping e SSH test para validar a interface. O Agent **NUNCA DEVERÁ** codar o setup de Worker.py sem rodar independentemente este script terminal primeiro.
- [ ] Autenticar chamadas inter-agentes no `worker_protocol.py` utilizando o IP dinâmico validado.
- [ ] **Redundância Híbrida**: Adicionar File Transfer físico (SCP) ao wrapper de conexão SSH no `worker_protocol.py`.
- [ ] **Recuperação de Amnésia**: Master lê `in_progress` da DB ao resetar via polling no `on_session_start` caçando tarefas órfãs abandonadas no S21.
- [ ] Kill Switch remetente: `/api/kill` propaga cancelamentos pro Android Escravo.

## Fase 10: Conselho Expandido (Blue/Red Team Distribuídos)
- [ ] Nova intenção `council` disparando `asyncio.gather` em provedores multi-modal (Groq, Cerebras, Kimi) consolidando com modelo Presidente.
- [ ] Lock do Conselho a 3 tentativas, balizado pelo `IARA_HITL_POLICY.md`.
- [ ] Lock do Blue Team S21 FE rejeitando perigos de sistema, com bail-out após 2 tentativas pro Telegram.

## Fase 11: Sandbox Absoluta (Decision WASM vs E2B Híbrida)
- [ ] Integrar extensão remota de nuvem robusta através da API E2B SDK.
- [ ] Abordagem Mista confirmada: Execuções nativas WASM ou Python puristas rodam na localidade; E2B isola workloads que drenam ciclos do hardware (Carga + ML).
- [ ] **Pipeline de Entrega**: Extrair arquivos e charts contidos no Cloud do E2B fazendo a descida local para o frontend SSE servir os buffers através da UI.

## Fase 12: Memória Contextual Orientada a Objeto (Full Stack Projects)
- [ ] Backend: SQLite FTS5 / Cohere Embeddings amarrados ao `project_id`.
- [ ] Retrieval: Na chegada do Prompt, o `brain.py` gera cossine query embeddings em real-time e recupera os TOP-K compatíveis injetando silenciosamente via System. 
- [ ] Frontend: Expor um endpoint `/api/projects`.
- [ ] Frontend React: Modificar Header do dashboard montando `<Select>` para troca passiva do projeto base.
