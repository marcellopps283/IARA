# Dossiê de Arquitetura: Projeto ZeroClaw 2.0
## 1. O Que Queremos Alcançar (O Objetivo Final)
- Descentralização (Monólito para Multi-Agente): Transformar a IA "Kitty" de um script único para uma arquitetura de orquestração. A Kitty será a "Gerente" (Master), e haverá agentes "Operários" (Workers), como Web Scrapers e Coders.
- Computação de Borda (Edge Computing): Dividir a carga de trabalho fisicamente. O S21 Ultra será o servidor de Orquestração/Atendimento, e o S21 FE será o servidor de Execução/Pesada.
- Comunicação Inter-Agentes: Fazer com que os celulares/agentes conversem entre si via rede Wi-Fi local (usando APIs leves) trocando pacotes de dados estruturados (JSON).
- Ciclo de Auto-Correção: Estabelecer um loop onde um agente escreve um código, o sistema testa, e se der erro, devolve para o agente consertar sozinho antes de mostrar ao usuário.
- Identidade Modular: Implementar a lógica do SOUL.md (arquivos de texto de identidade) para definir as regras e limites de cada agente de forma isolada.
## 2. O Que Já Foi Feito (O Ponto de Partida)
- Ponte de Desenvolvimento: O ambiente de programação remoto está 100% funcional. O PC conecta via túnel SSH diretamente ao Termux do S21 Ultra, permitindo edição de código ao vivo.
- Compatibilidade de Ambiente: O ecossistema base do Android (Bionic) foi domado. Instalamos as ferramentas GNU essenciais (wget, debianutils) e resolvemos os problemas de rotas de dependência (transplante do Node.js).
- A Semente Lógica: Temos a estrutura base (ZeroClaw) escrita em Python, composta por main.py, core.py (ferramentas) e personality.py / brain.py (memória), o que nos dá controle total sobre o código original.
## 3. Os Recursos Disponíveis (O Nosso Arsenal)
- Hardware:
  - Samsung Galaxy S21 Ultra (Poder de processamento alto, muita RAM - Nó Principal).
  - Samsung Galaxy S21 FE (Poder secundário - Nó Operário).
  - PC Windows (Cockpit de Desenvolvimento via Antigravity).
- Software & Infraestrutura:
  - Termux (Ambiente Linux emulado no Android).
  - Python (Linguagem base principal).
  - Rede Local (LAN / Wi-Fi) conectando os dispositivos.
  - Modelos de IA via API para dar inteligência aos agentes.