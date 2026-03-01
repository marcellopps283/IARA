# Estrutura do Repositório (Depth 2 e Arquivos Essenciais)

root/
- .agents/
- dashboard/
  - index.html
- docs/
- identity/
  - kitty_instructions.md
- roles/
  - pesquisador.md
  - revisor.md
- skills/
- brain.py (Ponto de entrada Assíncrono para o Master Iara no celular principal)
- core.py (Gerenciador SQL Persistente de Memórias, Lembretes e Jobs)
- config.py (Variáveis globais, limites de falha e tokens REDACTEDS)
- orchestrator.py (Scheduler assíncrono e balanceador Swarm)
- worker_protocol.py (Criação Subprocess e Pipes SSH para Workers)
- llm_router.py (Sistema LLM Agnostic de envio à OpenAI API Models, Fallbacks para Rate limit HTTP 429)
- run_task.py (Ciclo assíncrono Worker-Side local que ouve a porta stdin e dispara output stdout)
- network.py (Implementação experimental Zeoconf mDNS para auto-descobrir androids na rede)
- sandbox.py (Runtime PRoot isolador e chroot para códigos arbitrários executados pela Web)
- deep_research.py (Lógica Plan & Execute distribuída)
- doc_reader.py (Integra PDFPlumber e Docx para leitura crua de anexos locais)
- telegram_bot.py (Frontend aiogram para mensagens interativas com Markdown Stream)
- dashboard_api.py (Web Interface SSE de Streaming de mensagens sem block)
