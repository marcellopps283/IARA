# ZeroClaw 2.0 - Plano de Implantação e Deploy Fasedo

Este plano organiza a implantação da arquitetura P2P de Inteligência Artificial para operar nos seus 3 dispositivos *Edge*, garantindo que cada fase seja isolada da outra para não gerar *crash* no Master.

## Pré-Requisito Global (Todos os Aparelhos)
1. Certifique-se de que os aparelhos estejam na mesma rede Wi-Fi (ou via Roteador Local/Ethernet no caso do Moto G4).
2. Fixe os endereços IP dos aparelhos nas configurações do seu roteador (DHCP Estático) para que o Master sempre consiga alcançá-los:
   - **S21 Ultra:** `192.168.x.x` (Não precisa fixar obrigatoriamente, mas é bom)
   - **S21 FE (Heavy):** `192.168.x.A`
   - **Moto G4 (Light):** `192.168.x.B`

---

## FASE 1: Voo Solo do Orquestrador (Hoje)
**Alvo:** S21 Ultra (Terminal / Master Node)
**Status:** Operante (Não há dependência de outros Nodes)

1. **Instalação:** 
   - No Termux do S21 Ultra, use o comando `cat > codigo_projeto.json` e cole o conteúdo do arquivo exportado pelo PC.
   - Execute um script ou um comando Python puro para extrair (`import json, os` e instancie as pastas/arquivos localmente no S21).
   - Instale as dependências master:
     `pip install pyyaml diskcache rapidfuzz groq pydantic toml aiogram aiosqlite pyzmq httpx`

2. **Configuração de Ambiente:**
   - Crie o arquivo `.env` contendo **apenas** as chaves mestras:
     ```env
     TELEGRAM_BOT_TOKEN=seu_bot_token
     GROQ_API_KEY=gsk_sua_chave_aqui
     USER_ID_ALLOWED=seu_id_telegram
     ```
   - Não configure os IPs dos workers ainda (O Master assumirá `127.0.0.1` e engatilhará o Timeout Seguro de 15s sem quebrar).

3. **Execução:**
   - `python brain.py`
   - Mande mensagens pelo Telegram. Tente invocar uma Tool do worker e comprove que ele retornará falha amigavelmente por falta do Nó.

---

## FASE 2: Arsenal de Ferramentas (Semanas seguintes)
**Alvo:** S21 FE (Heavy Worker)
**Conexão:** Porta `5556`

1. **Instalação:**
   - Copie o **mesmo** `codigo_projeto.json` e extraia-o no Termux do S21 FE.
   - Instale as dependências pesadas:
     `pip install pyzmq composio-core mcp smolagents transformers`

2. **Configuração de Ambiente:**
   - Crie o `.env` no S21 FE contendo apenas as chaves SaaS:
     ```env
     COMPOSIO_API_KEY=sua_chave_composio
     ```
   - No S21 Ultra (Master), edite o `.env` declarando onde está o Heavy Worker:
     ```env
     HEAVY_WORKER_IP=192.168.x.A
     ```

3. **Execução:**
   - No S21 FE, execute: `python worker_main.py 5556`
   - Teste mandando a IA ler uma pauta no repositório GitHub via Composio, ou delegar a construção de um script complexo em Python para o `CodeAgent`.

---

## FASE 3: Painel Pessoal e Servidor Web (Futuro)
**Alvo:** Moto G4 (Light Worker / Mártir)
**Conexão:** Porta `5558` (Acorrentado via cabo de rede)

1. **Instalação:**
   - Copie o **mesmo** `codigo_projeto.json` e extraia.
   - Instale apenas o necessário para receber conexões:
     `pip install pyzmq` (Servidores HTTP e HTML puros usam bibliotecas padrão).

2. **Configuração de Ambiente:**
   - No S21 Ultra (Master), edite o `.env` declarando onde está o Light Worker:
     ```env
     LIGHT_WORKER_IP=192.168.x.B
     ```

3. **Execução:**
   - No Moto G4, execute: `python worker_main.py 5558`
   - Do Telegram, peça à Kitty: *"Crie um dashboard em HTML na pasta /dashboards com gráficos sobre nosso uso atual e coloque no ar."* O S21 Ultra transmitirá a carga para o Moto G4, que retornará o Link Mágico (IP Local) para acesso via iPhone.
