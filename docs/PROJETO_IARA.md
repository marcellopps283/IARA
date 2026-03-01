# Projeto Iara — Visão, Estado Atual e Roadmap

## A Ideia Central

Iara é um **assistente pessoal autônomo** que roda inteiramente em um Samsung Galaxy S21 Ultra com Termux — sem custos de servidor, sem nuvem obrigatória, sem assinatura mensal. A proposta é provar que é possível construir um agente de IA completo, com memória persistente, ferramentas reais e personalidade própria, usando **exclusivamente APIs gratuitas e hardware de bolso**.

O nome é uma referência à lenda brasileira da Iara — uma entidade inteligente que vive nas águas (e no nosso caso, nos fluxos de dados).

## Filosofia

- **Zero custo operacional**: toda a stack usa free tiers (Groq, Cerebras, NVIDIA NIM, Jina, DuckDuckGo)
- **Replicável**: qualquer pessoa com um Android e Termux consegue rodar
- **Evolutivo**: a Iara aprende sobre o dono ao longo do tempo (core memory, preferências)
- **Soberano**: seus dados ficam no SEU celular, não na nuvem de terceiros

## O que temos AGORA (funcionando em produção no S21 Ultra)

### Assistente completa via Telegram
- Chat natural com personalidade definida (identidade em 3 arquivos: SOUL, STYLE, SKILLS)
- Streaming real (edita mensagem token a token no Telegram)
- Responde em português brasileiro, com tom direto e sem formalidade corporativa

### Inteligência multi-LLM
- 4 provedores configurados com fallback automático: Groq (Llama 70B) → Kimi K2.5 (NVIDIA NIM) → Cerebras (Llama 8B) → OpenRouter (DeepSeek R1)
- Se um cai ou dá rate limit, o próximo assume sem o usuário perceber
- Consumo eficiente: <2% da quota diária do Groq num dia pesado

### Memória em 3 camadas
- **Working**: últimas 20 mensagens (RAM da conversa)
- **Episodic**: resumos de conversas passadas, pesquisáveis por keyword
- **Core**: fatos permanentes sobre o dono (ex: "gosta de café sem açúcar"), com nível de confiança

### Ferramentas (Tools) ativas
- Pesquisa web (Jina → DDG → Brave, cascata de fallback)
- Leitura completa de URLs (Jina Reader → Markdown)
- Análise de documentos (PDF, DOCX, TXT, CSV, XLSX enviados via Telegram)
- Clima em tempo real (Open-Meteo, sem key)
- Status do dispositivo (bateria, storage, rede)
- Lembretes agendáveis ("me lembra daqui a 30 min")
- Deep Research Plan & Execute (ver abaixo)

### Deep Research (inspirado no Gemini Deep Research)
- LLM decompõe o tema em 4-6 sub-tarefas
- Mostra plano pro usuário aprovar antes de executar
- Execução iterativa: busca → lê → detecta lacunas → busca mais
- Progresso em tempo real no Telegram
- Relatório final com citações granulares [1], [2]
- Relatórios longos enviados como arquivo .md

### Multi-agente (Swarm SSH)
- S21 FE configurado como worker remoto via SSH
- Delegação de tarefas: orquestrador (Ultra) → worker (FE)
- Cada worker usa suas próprias API keys (multiplica quotas)
- Comandos /worker add|remove|list|ping

### Comportamentos autônomos
- Auto-detecção de fatos pessoais (salva em core memory sem ser pedido)
- Auto-reflexão (avalia qualidade das próprias respostas, toggle /reflect)
- Preference learning (a cada 30min analisa padrões e salva como preferências)
- Compactação automática de memória (quando working > 20 msgs)

## O que queremos fazer (Roadmap)

### Curto prazo
- [ ] Criar contas Groq/Cerebras separadas pro S21 FE (multiplicar quotas de verdade)
- [ ] Testar delegação paralela (fan-out: Ultra + FE buscam ao mesmo tempo)
- [ ] Integrar Perplexity Pro como fonte de pesquisa (se API ficar disponível)
- [ ] Dashboard visual (Telegram Mini App) com: stats de uso, mapa de workers, biblioteca de pesquisas

### Médio prazo
- [ ] Workers na nuvem (Modal, fly.io) além dos celulares
- [ ] Execução de código em sandbox seguro
- [ ] Automação web (navegação em sites, preenchimento de formulários)
- [ ] Integração com Google Drive/Sheets (exportar pesquisas)
- [ ] Sistema de plugins (skills declarativas com manifest.toml)

### Longo prazo
- [ ] Kimi K2.5 Agent Swarm Mode (subagentes internos do modelo)
- [ ] Auto-deploy de workers (detecta novo device na rede → configura sozinho)
- [ ] Orquestração multi-modelo (Groq pro chat, Kimi pro research, DeepSeek pro raciocínio)
- [ ] Modo offline parcial (cache local de respostas frequentes)

## Stack técnica

| Camada | Tecnologia |
|--------|-----------|
| Runtime | Python 3.12 no Termux (Android) |
| Interface | Telegram Bot API (aiogram) |
| LLMs | Groq, Cerebras, NVIDIA NIM, OpenRouter (todos free tier) |
| Busca | Jina Search, DuckDuckGo, Brave API |
| Persistência | SQLite (aiosqlite) |
| Comunicação | SSH (entre devices), aiohttp (APIs) |
| Config | python-dotenv (.env por device) |

## Limitações conhecidas
- Sem embeddings (busca em episodic é keyword-based, não semântica)
- Sem execução de código (sandbox existe mas não está ativo)
- Workers dependem de WiFi local (SSH) — sem NAT traversal ainda
- Kimi K2.5 tem apenas 1000 créditos NIM (usado como fallback)
