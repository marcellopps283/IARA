# IARA v2 — Arquitetura "Agentic" Completa e Consolidação (Revisão Pós-Pesquisa)

Este plano unifica as ideias avançadas extraídas dos arquivos da pasta `maisnovo` e as alinha com a infraestrutura atual (Local-First Edge Swarm no Termux via S21 Ultra e S21 FE).

## User Review Required

Nenhuma inconsistência pendente. Todas as limitações de hardware e de rede do ecossistema Android/Termux foram resolvidas com estratégias de fallback aprovadas:
1. **Paralelismo**: Adotada **Fila Estrita Sequencial** (máx. 2 tarefas ativas) no lugar de multiprocessamento irrestrito. Git Worktrees serão usados apenas como ambiente de staging seguro e explícito no **KittyFE (via SSH)**, poupando a RAM do Master.
2. **Memória Vetorial**: Substituição do inviável ChromaDB/`sqlite-vss` por **Google Gemini Embeddings API + SQLite FTS5 (nativo)** e pure-Python Cosine Similarity, garantindo zero quebras de compilação em ARM.
3. **Aprovação Ativa**: O **Telegram** continuará sendo a via exclusiva e soberana de aprovação (botões inline). O frontend Web funcionará como painel de histórico e monitoramento passivo.
4. **Rate Limits**: Implementação de um **Token Bucket nativo** no `llm_router.py` por provedor, rotacionando LLMs gratuitos de acordo com a fase de pipeline, evitando banimentos por "Too Many Requests".

## Proposed Changes: Fases de Evolução Estrutural

### 1. Sistema de "Canais de Mensagem" + Hooks de Defesa
Em vez de um único fluxo de pensamento, a IARA precisa esconder a "bagunça cognitiva" e se defender contra quebras de segurança.
- **[MODIFY] `brain.py` e `telegram_bot.py`:**
  - `analysis` (Privado): Core de pensamento (Chain-of-Thought), planejamento e leitura crua.
  - `commentary` (Público): Avisos curtos via Telegram/UI (Ex: "*Lendo o arquivo x...*").
  - `final` (Público): O output formal e definitivo ou solicitações de ações irreversíveis.
- **[NEW] `hooks.py`:** Eventos estáticos do sistema de onde outras rotinas se penduram.
  - **Segurança (CRÍTICO)**: `beforeShellExecution` (trava perigos Linux) e `beforeSubmitPrompt` (intercepta credenciais vazadas).
  - **Memória & Evolução**: `SessionStartHook`, `PreCompactHook` e o fundamental **`SessionEndHook`** (âncora principal do sistema de Instintos).

### 2. Máquina de Estado Robusta (Stateful Tasking)
- **[MODIFY] `orchestrator.py` / `core.py`:**
  - Criar um **TodoWrite System** em SQLite (`tasks_state`).
  - Regras: `pending` -> `in_progress` -> `completed`.
  - Apenas **1 tarefa** em `in_progress` por vez. Falhas reinjetam sub-tarefas de autocorreção em vez de apagar o progresso.

### 3. Plan Mode Toggle & Sistema "Council" Deliberativo
Trava anti-ansiedade que evita a IARA de sair codificando loucamente e quebrando a base.
- **[NEW Tools]** `EnterPlanMode` e `ExitPlanMode` integrados fortemente ao **Council**:
  - Antes do código, sub-agentes do Conselho Deliberativo (`Planner`, `Architect`, `Security`) debatem a solução ideal usando a ferramenta `Explore` (grep/glob no código).
  - O documento gerado (`plan.md`) requer aprovação explícita pelo Telegram.

### 4. Execução em Cascata de 5 Fases
O novo coração do pipeline. Tarefas complexas seguem esta roteirização obrigatória (roteando LLMs conforme o custo-benefício via Token Bucket):
1. `RESEARCH` -> Produz `research-summary.md` no tmp.
2. **`PLAN` (Council Delibera)** -> Gera o `plan.md` com arquitetura inicial e suspende no Telegram.
3. `IMPLEMENT` -> Executado sequencialmente + TDD.
4. **`REVIEW` (Council Ataca)** -> Sub-agentes `Code Reviewer`, `Security Reviewer` e `Auditor` formam o Red/Blue Team e geram `review-comments.md`. Se crítico, trava.
5. `VERIFY` -> Build resolver confirma a execução.

### 5. Memória (RAG Melhorado) e Instintos Contínuos
Reforma do `CONTEXTO_IA.md` e injeção semântica evolutiva.
- **Configuração da Injeção (4 Camadas)**: Metadados, Preferências, Tópicos e Conteúdo Recente inseridos estrategicamente sob demanda.
- **Aprendizado Contínuo (Instintos)**:
  - O **`SessionEndHook`** extrai "o que funcionou/falhou" gerando anotações com "Confidence Score".
  - **Critério de Evolução**: Acumular 3+ instintos similares com score >= 0.7 faz com que o agente os agrupe e crie automaticamente um `SKILL.md` na pasta `skills/`.
  - **Âncora de Execução**: Esse ciclo pesado de promoção (Instinto -> Skill) não roda no runtime principal, ele tira proveito do **loop noturno das 3h da manhã já existente no `memory_core_skill.py`**, que ganha assim seu segundo grande papel (fazer o fechamento diário e evoluir habilidades).

## Verification Plan

### Automated Tests
1. Testar se as mensagens do canal `analysis` ficam efetivamente mascaradas do banco do frontend e envios de requisição do Telegram (certificando-se de que não estamos gastando tokens enviando lixo via rede).
2. Forçar execução de comando de deleção proibido (`rm -rf`) via bash agent para garantir que o `beforeShellExecution` em `hooks.py` barre antes do Subprocess ser invocado.
3. Validar busca semântica do RAG utilizando SQLite FTS5 indexado pelo BM25 nativo.

### Manual Verification
1. Criar e autorizar uma tarefa destrutiva que passará pelas 5 Fases. Observar se o roteador de modelos no Console troca a _engine_ ativa baseando-se no `task_type` de acordo com a fase (`gemini` -> `cerebras` -> `kimi` -> etc), acionando o Backoff do Token Bucket se necessário.
2. Interceptar a `Fase 4 (REVIEW)` simulando a injeção manual de um token/senha falsa na UI. Confirmar se o `beforeSubmitPrompt` paralisa e alerta, como planejado no Red Team Audit.
3. **Teste do Ciclo de Instintos (Fase 5)**: Simular uma sessão onde um padrão repetitivo é ensinado. Validar se o `SessionEndHook` gerou o micro-arquivo de instinto no final. Repetir isso 3 vezes simuladas e acionar manualmente o script das 3h da manhã (`memory_core_skill.py`) para confirmar se o agrupamento gerou corretamente um novo arquivo `.md` na pasta `skills/`.
