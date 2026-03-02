# I.A.R.A — Human-in-the-Loop (HITL) Policy

Este documento estabelece as regras de suspensão ativa do sistema para solicitar a intervenção humana (Criador) via Telegram. O objetivo é evitar ações destrutivas, alucinações caras em nuvem, e loops infinitos no Conselho.

## Níveis de Risco e Gatilhos

### 1. Nível SAFE (Verde)
**Definição**: Tarefas exploratórias, computacionais locais sem efeito destrutivo ou com escopo restrito de tokens.
**Exemplos**:
- Responder a perguntas do chat.
- Realizar Deep Research na internet.
- Ler arquivos locais no Termux (/sdcard ou /projetin).
- Executar scripts Python locais (WASM ou Proot) focados em dados que não interagem com o sistema de arquivos base.
**Ação da IARA**: **Execução autônoma direta**. Sem necessidade de pingar o humano, exceto por logs passivos via canal `commentary`.

### 2. Nível MEDIUM (Amarelo)
**Definição**: Tarefas que podem alterar o estado do projeto, consumir muitos recursos de terceiros ou estagnar por indecisão do LLM.
**Exemplos**:
- Escrita ou sobrescrita de arquivos e scripts fonte (*Implement*).
- Despacho de análises maciças de Data Science para a E2B Nuvem (custo financeiro).
- Falha de Consenso no "Presidente" do Conselho após a 2ª tentativa.
- Falha de aprovação do código (Blue Team) após a 1ª tentativa.
**Ação da IARA**: **Alerta e Pausa Condicional**. Notifica via Telegram (`final`). O Dashboard e os agentes aguardam um fluxo interativo simplificado. Pode haver regras de timeout que autorizem a continuação se a Confidence for alta.

### 3. Nível HIGH RISK (Vermelho)
**Definição**: Ações que representam risco de segurança absoluto (data loss), custos astronômicos, ou exaustão de limites (Quotas).
**Exemplos**:
- Excluir diretórios recursivamente (`rm -rf`) detectados no Red Team Review.
- Manipulação de pastas restritas do SO Android (`/data/data/com.termux`).
- Consenso de Conselho falho 3 vezes (Loop Infinito Abortado).
- Blue Team rejeita script da Sandbox do Master 2 vezes (Risco de Injeção Persistente).
- Cota Diária de Tokens (`MAX_DAILY_LLM_CALLS`) atingida - Prevenção de Falência.
- Modificação na injeção de `hooks.py` de Defesa.
**Ação da IARA**: **Paralisação Total Imediata (Hard Stop)**. Todas as tarefas em `in_progress` mudam para `pending`. O sistema entra em trava térmica (Lock) e recusa prosseguir. O humano deve reabrir a catraca ativamente via Comando ou Botão no Dashboard/Telegram.
