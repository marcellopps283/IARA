# ENTREGA A — Visão Geral do Projeto Iara

## O que é
Iara (Interface de Acionamento da Rede de Agentes) é um **assistente pessoal autônomo** rodando em Android (Termux) em um Samsung Galaxy S21 Ultra, acessível via Telegram. Ela funciona como um orquestrador de agentes: recebe mensagens, classifica a intenção (chat, busca, pesquisa profunda, lembretes, clima, memória), executa ferramentas (tools) e responde via LLM com streaming. Possui memória persistente em 3 camadas, personalidade própria definida em arquivos de identidade, e capacidade de auto-reflexão.

## Como rodar
```bash
# No S21 Ultra via Termux:
cd ~/KittyClaw
python brain.py

# Ou via restart script:
bash restart.sh
```

## Agentes/Módulos
- **brain.py** — Orquestrador principal: classify intent → execute tool → LLM response → auto-detect memory → auto-reflect
- **core.py** — Persistência: 3 camadas de memória (Working/Episodic/Core) + lembretes + reflexões via SQLite
- **llm_router.py** — Roteador multi-LLM com fallback automático: Groq (Llama 70B) → Kimi K2.5 (NVIDIA NIM) → Cerebras (Llama 8B) → OpenRouter (DeepSeek R1)
- **telegram_bot.py** — Interface Telegram com streaming (edita mensagem token a token), envio de documentos .md para mensagens longas
- **deep_research.py** — Pesquisa profunda "Plan & Execute": LLM decompõe tema → mostra plano → usuário aprova → execução iterativa com detecção de lacunas → relatório com citações [1][2]
- **web_search.py** — Cascata de busca: Jina Search → DuckDuckGo → Brave Search. Leitura de URLs via Jina Reader
- **worker_protocol.py** — Delegação de tarefas para workers remotos via SSH (S21 FE como worker)
- **run_task.py** — Executor standalone para workers: recebe JSON via stdin, executa com keys locais, retorna JSON
- **doc_reader.py** — Análise de documentos enviados pelo usuário (PDF, DOCX, TXT, CSV, XLSX)
- **skills/** — Sistema de tools dinâmico: skills carregadas de arquivos _skill.py ou pastas com manifest.toml

## Ferramentas (Tools) disponíveis
- **web_search** — Busca na web (Jina/DDG/Brave)
- **web_read** — Leitura completa de URLs (Jina Reader)
- **save_core_fact** — Salvar fato permanente na core memory
- **get_weather** — Clima via Open-Meteo (grátis, sem API key)
- **get_system_status** — Bateria, storage, rede do dispositivo
- **save_reminder** — Agendar lembretes com loop de verificação a cada 30s
- **deep_research** — Pesquisa profunda Plan & Execute (4-6 sub-tarefas iterativas)
- **doc_analysis** — Análise de PDFs, DOCX, TXT, CSV, XLSX enviados via Telegram

## Loop de execução (brain.py:process_message)
1. Mensagem chega via Telegram
2. Verifica comandos especiais (/think, /reflect, /worker, arquivos)
3. Verifica se há plano de pesquisa pendente de aprovação
4. Salva mensagem na working memory
5. Classifica intent (keywords rápidas → LLM fallback)
6. Executa tool correspondente ao intent
7. Monta system prompt (identidade + core memory + reflexões + episódios)
8. Chama LLM via streaming, edita mensagem no Telegram em tempo real
9. Auto-detect: salva fatos pessoais detectados na resposta (background)
10. Auto-reflect: avalia qualidade da resposta (background, se ativado)
11. Compacta working memory se ultrapassar 20 mensagens (salva resumo em episodic)
12. Preference learning: a cada 30min analisa padrões recorrentes nos episódios

## Memória e estado
- **Working Memory** — SQLite, últimas 20 mensagens (curto prazo)
- **Episodic Memory** — SQLite, resumos de conversas compactadas (médio prazo)
- **Core Memory** — SQLite, fatos permanentes sobre o usuário com categoria e confiança (longo prazo)
- **Reflections** — SQLite, lições aprendidas pela auto-reflexão
- **Reminders** — SQLite, lembretes agendados com loop de verificação
- **Identidade** — Arquivos .md em identity/ (SOUL.md, SKILLS.md, STYLE.md)

## Swarm Multi-Agente (em desenvolvimento)
- S21 Ultra = orquestrador principal
- S21 FE = worker conectado via SSH (já configurado)
- Cada worker tem suas próprias API keys (multiplica quotas gratuitas)
- worker_protocol.py gerencia registro, health check, delegação e fan-out paralelo
