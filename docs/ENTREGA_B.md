# ENTREGA B — Estrutura do Repositório

## Árvore de diretórios (profundidade 4)

```
KittyClaw/
├── brain.py                   # Orquestrador principal (entry point)
├── config.py                  # Configuração centralizada + API keys
├── core.py                    # Memória 3 camadas (SQLite)
├── llm_router.py              # Roteador multi-LLM com fallback
├── telegram_bot.py            # Interface Telegram (streaming + docs)
├── deep_research.py           # Pesquisa Plan & Execute
├── web_search.py              # Cascata de busca web
├── worker_protocol.py         # Delegação SSH entre dispositivos
├── run_task.py                # Executor standalone para workers
├── doc_reader.py              # Análise de documentos (PDF/DOCX/etc)
├── sandbox.py                 # Sandbox para execução de código
├── network.py                 # Utilitários de rede
├── transport.py               # ZeroMQ transport (futuro)
├── worker_main.py             # Worker main loop (futuro)
├── drive_sync.py              # Sync com Google Drive (futuro)
├── export_json.py             # Exportador de conversas
├── instalar.py                # Script de instalação
├── restart.sh                 # Script de restart
├── requirements.txt           # Dependências Python
├── kitty_mem.db               # SQLite database (memória)
├── .env                       # API keys (NÃO incluir)
│
├── identity/                  # Definição de personalidade
│   ├── SOUL.md                # Quem é a Iara (personalidade)
│   ├── SKILLS.md              # O que ela pode fazer
│   └── STYLE.md               # Como ela fala
│
├── skills/                    # Tools dinâmicas
│   ├── __init__.py
│   ├── skills_registry.py     # Carregador dinâmico de skills
│   ├── jina_reader_skill.py   # Skill: leitura de URLs
│   ├── memory_core_skill.py   # Skill: salvar fatos permanentes
│   ├── open_meteo_skill.py    # Skill: clima/previsão
│   └── system_status_skill.py # Skill: status do dispositivo
│
├── skills_archive/            # Skills desativadas/backup
│
└── docs/                      # Documentos de referência (user uploads)
    └── (17 arquivos de pesquisa — não fazem parte do código)
```

## 15 arquivos mais importantes

| # | Arquivo | Linhas | Por quê |
|---|---------|--------|---------|
| 1 | brain.py | 668 | Entry point, orquestrador: classify intent → tool → LLM → respond |
| 2 | core.py | 485 | Toda a persistência: 3 camadas de memória, lembretes, reflexões |
| 3 | config.py | 95 | Configuração centralizada, providers LLM, paths, limites |
| 4 | llm_router.py | 202 | Roteador multi-LLM com fallback automático e streaming |
| 5 | deep_research.py | 290 | Pesquisa profunda Plan & Execute com citações |
| 6 | telegram_bot.py | 260 | Interface Telegram: streaming, sanitização, envio de docs |
| 7 | web_search.py | 200 | Cascata de busca: Jina → DDG → Brave + leitura de URLs |
| 8 | worker_protocol.py | 160 | SSH delegation: registro, health check, fan-out paralelo |
| 9 | run_task.py | 100 | Executor standalone para workers (JSON in → JSON out) |
| 10 | identity/SOUL.md | 38 | Define personalidade, instintos, limites éticos |
| 11 | identity/STYLE.md | 39 | Define tom de voz, formatação, anti-patterns |
| 12 | identity/SKILLS.md | 35 | Lista habilidades ativas e futuras |
| 13 | skills/skills_registry.py | 84 | Carregador dinâmico de tools (legacy .py + declarativo TOML) |
| 14 | doc_reader.py | 160 | Parse de PDFs, DOCX, TXT, CSV, XLSX |
| 15 | restart.sh | 20 | Script que mata processos antigos e reinicia |
