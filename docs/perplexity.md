\# Exportar projeto (Snapshot textual) para análise arquitetural

\#\# Objetivo  
Gerar um snapshot textual do meu projeto (swarm/orquestrador de agentes) para que um assistente possa analisar contexto, arquitetura, fluxos, ferramentas (tools) e pontos de melhoria.

Você (agente no Antigravity) deve \*\*coletar informações do repositório\*\*, \*\*sanitizar segredos\*\*, e \*\*entregar a saída em formato padronizado\*\*.

\---

\#\# Regras obrigatórias (segurança e privacidade)  
1\. \*\*Nunca\*\* inclua segredos, mesmo que pareçam inofensivos:  
   \- \`.env\`, chaves, tokens, cookies, credenciais, refresh tokens, API keys, JWTs.  
   \- Strings suspeitas (ex.: começando com \`sk-\`, \`AIza\`, \`ghp\_\`, etc.).  
   \- URLs privadas, endpoints internos, IPs internos, nomes de buckets privados.  
2\. Onde existir segredo, substitua por \`\_\_REDACTED\_\_\`.  
   \- Exemplo: \`OPENAI\_API\_KEY=\_\_REDACTED\_\_\`  
3\. Se houver dados pessoais (email, telefone, endereço, nomes reais), mascare:  
   \- \`lucas@email.com\` → \`\_\_REDACTED\_EMAIL\_\_\`  
4\. Em logs/traces, \*\*remova payloads\*\* que possam conter dados sensíveis.  
5\. Se tiver dúvida se algo é sensível, \*\*mascare\*\*.

\---

\#\# Instruções de entrega (3 partes)  
Você deve entregar em \*\*3 mensagens\*\* (ou 3 arquivos), nesta ordem.

\#\#\# ENTREGA A — Visão geral (máximo 200 linhas)  
Inclua:  
\- O que o sistema faz (1 parágrafo).  
\- Como rodar (comandos básicos).  
\- Quais agentes existem e a responsabilidade de cada um.  
\- Quais tools/capacidades existem (filesystem, browser, http, search, scheduler, memory, etc.).  
\- Como funciona o loop de execução (roteamento / decisão do próximo passo).  
\- Como estado/memória é mantido (arquivos, DB, embeddings, resumos).

Formato sugerido:  
\- 5–12 bullets, cada bullet com 1–2 frases.

\---

\#\#\# ENTREGA B — Estrutura do repositório  
1\) Gere uma \*\*árvore de diretórios\*\* até profundidade 4, incluindo arquivos relevantes.

2\) Liste os \*\*15 arquivos mais importantes\*\* e por quê (1 linha por arquivo).

Exemplo de árvore:  
\- \`root/\`  
\- \`root/src/\`  
\- \`root/src/orchestrator.py\`  
\- \`root/src/agents/\`  
\- \`root/src/tools/\`

\---

\#\#\# ENTREGA C — Conteúdo selecionado (somente arquivos-chave)  
Inclua \*\*conteúdo integral\*\* apenas do que for essencial para entender o sistema:

\- README / docs de arquitetura (se houver).  
\- Arquivo(s) de entrada do orquestrador (\`main.\*\`, \`app.\*\`, \`index.\*\`, etc.).  
\- Definição de agentes (prompts/roles/policies).  
\- Definição de tools (schemas \+ handlers).  
\- Memória/estado (persistência, formatos, embeddings se houver).  
\- Scheduler/loop principal (fila, retries, limites).  
\- Configuração (sem segredos).

\#\#\#\# Limite de tamanho por arquivo  
\- Se algum arquivo tiver \*\*mais de 300 linhas\*\*, não cole inteiro.  
  \- Inclua: cabeçalho \+ trechos relevantes \+ um resumo do restante.  
  \- Preserve assinaturas de funções/classes e pontos de integração.

\---

\#\# Formato PADRÃO para cada arquivo incluído  
Para cada arquivo que você inserir na ENTREGA C, use \*\*exatamente\*\* este envelope:

\--- FILE: caminho/arquivo.ext \---  
(conteúdo aqui)  
\--- END FILE \---

Regras:  
\- Respeite o caminho real do arquivo.  
\- Não altere a ordem das seções dentro do arquivo.  
\- Se você omitir trechos longos, use:  
  \- \`\[...\] OMITIDO: motivo \+ quantidade aproximada de linhas\`

\---

\#\# Checklist final (antes de enviar)  
\- \[ \] Não há chaves/tokens/credenciais.  
\- \[ \] Não há \`.env\` real.  
\- \[ \] Dados pessoais foram mascarados.  
\- \[ \] A ENTREGA A está abaixo de 200 linhas.  
\- \[ \] A ENTREGA B tem árvore até profundidade 4\.  
\- \[ \] A ENTREGA C tem apenas arquivos-chave, com envelopes \`--- FILE \---\`.

\---

\#\# Importante  
Se o projeto estiver “espalhado” (parte em docs, parte em pastas diferentes), explique isso na ENTREGA A e indique onde estão as partes.

Agora execute a coleta e envie: ENTREGA A, depois ENTREGA B, depois ENTREGA C (em blocos).

