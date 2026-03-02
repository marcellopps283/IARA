# I.A.R.A — Plano de Implementação v2 (Arquitetura Agentic)

## Fase 0: Fundação ✅
- [x] Otimização e reestruturação da base (brain, orchestrator, deep_research)
- [x] Frontend Web UI (React + Vite + shadcn) PWA com suporte iOS
- [x] Integrações nativas PWA e Backup automático Google Drive SQLite
- [ ] Criar `IARA_HITL_POLICY.md` (Human-in-the-Loop Policy para níveis Safe/Medium/High)

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

## Fase 7: Roteamento Escalável e Contexto Econômico (Fast vs Heavy)
- [ ] Atualizar `classify_intent` para repassar `require_fast=True` ao router em chats normais.
- [ ] Rotear requisições fast pro Groq, permitindo fallbacks e escalate pra modelos Reasoning (OpenRouter/R1) em caso de refatoração ou erro.

## Fase 8: Resiliência de Malha e Conexão (Tailscale SSH/SCP)
- [ ] **Teste 01**: Script estúpido de "Ping Test" para testar a porta SSH do S21 FE através do túnel 100.x Tailscale antes de avançar.
- [ ] Parametrizar configuração de IP no `config.py` e remover ZeroConf instável.
- [ ] Autenticar chamadas inter-agentes no `worker_protocol.py` diretamente por ssh 100.x.x.x.
- [ ] **Transporte Físico (SCP)**: Implementar envio direto de arquivos grandes ao Worker (via `scp -P 2022`) no `worker_protocol.py` antes da injeção de scripts de análise.
- [ ] **Recuperação de Amnésia**: Modificar o on_session_start do Master (`hooks.py` ou `brain.py`) para pingar o S21 FE buscando tarefas órfãs finalizadas durante quedas do Master.
- [ ] Hook de Cancelamento e endpoint `/api/kill` com `asyncio.Event` (GlobalCancellationToken). Deverá propagar o comando de cancelamento via SSH para o Worker (S21 FE) limpando memória ativamente.

## Fase 9: Conselho Expandido (Blue/Red Team Distribuídos)
- [ ] Nova intenção `council` disparando `asyncio.gather` em provedores multi-modal (Groq, Cerebras, Kimi) consolidando com modelo Presidente.
- [ ] **Lock de Suborno (Presidente)**: Limitar o loop de "Refinamento" de Conselho a 3 tentativas. Se exceder, pedir intervenção Humana.
- [ ] **Lock de Suborno (Blue Team)**: Se S21 FE rejeitar o código payload, o S21 Ultra tentará reescrever e consertar 2 vezes. Se persistir a falha de Auditoria, o fluxo trava para intervenção Humana.

## Fase 10: Sandbox Absoluta (Decision WASM vs E2B Híbrida)
- [ ] Integrar extensão remota e E2B SDK.
- [ ] Abordagem Híbrida confirmada: As ferramentas irão diferenciar nativamente e julgarão (WASM local nativo / E2B SDK Nuvem).

## Fase 11: Memória Contextual Orientada a Objeto (Projetos & Vectors)
- [ ] Tabela de `projects` (SQLite FTS5 / Cohere Embeddings).
- [ ] Relacionar conversas e `project_id`.
- [ ] API backend para troca de projeto pela Interface Web.

## Fase 12: Orquestração Visual (Web Dashboard & SSE) [Atrasado a Pedido]
- [ ] Modificar `dashboard_api.py` para Server-Sent Events (SSE).
- [ ] Expandir endpoint `/api/chat` para emitir tags de "pensamento" (STATUS, THINKING, ANSWER).
