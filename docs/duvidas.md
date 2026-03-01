Precisamos desenhar a arquitetura base para evitar gargalos de escalabilidade, controle de estado e consumo de tokens.

Por favor, analise as perguntas abaixo e proponha soluções de arquitetura para o nosso código:

#### **1\. Roteamento e Chamada de Ferramentas (Routing & Function Calling)**

* Como vamos garantir que o Orquestrador sempre devolva a decisão em um formato estruturado (como JSON) que o nosso código Python consiga ler sem quebrar?  
* O que acontece se o Orquestrador "alucinar" e tentar chamar um *Worker* que não existe, ou passar os parâmetros errados para a função? Como vamos implementar um loop de repetição (*retry logic*) para ele se corrigir sozinho antes de devolver um erro para o usuário?  
* Como vamos mapear dinamicamente as funções Python para que o Orquestrador saiba exatamente quais *workers* estão disponíveis a qualquer momento?

#### **2\. Gerenciamento de Memória e Contexto (State Management)**

* A IA Pessoal precisa de todo o histórico da conversa com o usuário. Porém, o *Worker* que faz uma pesquisa no Google só precisa do termo de busca. Como vamos separar e isolar as listas de mensagens (`messages = []`) na memória para não enviar o histórico inteiro para os *workers* (o que gastaria muitos tokens)?  
* Se um *Worker* precisar do resultado do trabalho de outro *Worker* para terminar sua tarefa, como faremos essa passagem de bastão (estado) no Python puro?

#### **3\. Execução Paralela (Assincronicidade e Performance)**

* Se o Orquestrador decidir que precisamos de 3 informações diferentes (ex: ler um PDF, buscar na web e consultar um banco de dados), como vamos estruturar o código com `asyncio` para que esses 3 *workers* rodem ao mesmo tempo em paralelo, em vez de um esperar o outro?  
* O que o nosso sistema deve fazer se 2 *workers* terminarem rápido, mas o terceiro ficar travado por *timeout* da API?

#### **4\. Observabilidade e Logs (Debugging)**

* Quando o sistema estiver rodando de forma autônoma na VPS, como vamos saber exatamente o que o Orquestrador pensou e quais *workers* ele chamou? Como você sugere estruturarmos os *logs* em Python para rastrear essa "árvore" de decisões sem poluir o terminal inteiro?

