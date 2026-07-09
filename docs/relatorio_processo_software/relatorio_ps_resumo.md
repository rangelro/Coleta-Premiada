# Relatorio de Processo de Software - Resumo

## 1. Identificacao do grupo

O projeto Coleta Premiada foi desenvolvido pelo grupo composto por Luis, Rangel, Heitor e Enzo. Durante o desenvolvimento, Heitor foi considerado o Scrum Master do grupo, atuando como apoio na organizacao das demandas, alinhamento entre integrantes e acompanhamento do andamento geral das tarefas.

O trabalho foi dividido entre diferentes repositorios do ecossistema:

- `Coleta-Premiada`: backend principal/Core em Django.
- `cp-collection-ms`: microservico de coleta.
- `coleta-premiada-frontend`: aplicacao frontend.
- `coleta-observability`: observabilidade com Prometheus e Grafana.

## 2. Processo de software adotado

O grupo adotou um processo hibrido, mesclando praticas de Scrum e Kanban. A escolha ocorreu porque o grupo precisava de organizacao por tarefas e acompanhamento visual do progresso, mas nao possuia uma rotina fixa de reunioes em dias pre-definidos.

Na pratica, o Scrum foi utilizado como referencia para organizar o trabalho em ciclos de entrega, discutir prioridades, revisar o que estava em andamento e realizar alinhamentos entre os integrantes. Ja o Kanban foi usado para visualizar o fluxo das atividades por meio de um quadro no GitHub Projects.

O processo real utilizado foi adaptativo: as reunioes e alinhamentos aconteciam conforme surgiam demandas, bloqueios ou oportunidades de encontro. Esses alinhamentos ocorreram principalmente por WhatsApp, reunioes online e encontros presenciais.

## 3. Organizacao das tarefas

Para organizar as demandas, foi criado um projeto no GitHub com um quadro Kanban contendo as seguintes colunas:

- Backlog
- Ready
- In Progress
- In Review
- Done

As tarefas eram criadas como issues e movidas no quadro conforme o progresso. O Backlog concentrava ideias e demandas ainda nao iniciadas. A coluna Ready representava tarefas prontas para desenvolvimento. A coluna In Progress indicava tarefas em execucao. A coluna In Review era usada para atividades em revisao ou aguardando validacao. A coluna Done representava tarefas concluidas.

Conforme o projeto progredia, o grupo decidia coletivamente quais tarefas cada integrante assumiria. Essas decisoes eram feitas a partir da necessidade do projeto, da disponibilidade dos membros e da area de maior afinidade ou contexto tecnico de cada um.

## 4. Conducao das sprints e iteracoes

Embora o grupo tenha usado Scrum como referencia, as sprints nao seguiram um calendario rigido com datas fixas de inicio, fim e reunioes obrigatorias. O trabalho foi conduzido em iteracoes naturais, acompanhando as entregas necessarias em cada etapa do projeto.

No inicio, o foco principal foi o planejamento da arquitetura e a organizacao do backend. Essa decisao foi importante porque o backend concentrava as regras de negocio principais, integracoes com banco de dados, mensageria, autenticacao, auditoria e comunicacao com o microservico.

Depois da base arquitetural, as iteracoes passaram a incluir:

- implementacao de regras de negocio do programa de pontos;
- integracao entre Core e microservico por RabbitMQ;
- desenvolvimento do microservico de coleta;
- criacao do frontend;
- autenticacao e telas principais;
- auditoria e logs;
- monitoramento e observabilidade;
- backup e restore;
- documentacao tecnica e arquitetural.

As prioridades eram revisadas conforme o grupo identificava novas dependencias ou dificuldades. Dessa forma, o processo foi mais flexivel do que um Scrum tradicional, mas manteve uma estrutura de acompanhamento baseada em tarefas, revisoes e entregas incrementais.

## 5. Cerimonias e comunicacao

As cerimonias foram adaptadas a realidade do grupo. Nao houve uma agenda formal fixa para daily, planning, review e retrospectiva em todos os ciclos. Em vez disso, os alinhamentos aconteciam quando havia necessidade de decisao ou quando algum integrante encontrava bloqueios.

As principais formas de comunicacao foram:

- grupo no WhatsApp;
- reunioes online;
- conversas presenciais;
- comentarios e organizacao por issues e pull requests no GitHub.

As reunioes eram usadas para discutir prioridades, dividir tarefas, resolver duvidas de integracao e decidir proximos passos. O WhatsApp foi o canal mais rapido para comunicacao diaria e ajustes pontuais.

## 6. Priorizacao dos requisitos

Os requisitos foram priorizados considerando dependencias tecnicas e valor para o funcionamento do sistema. O grupo priorizou primeiro a arquitetura e o backend, pois o Core era a base para autenticar usuarios, cadastrar entidades principais, aplicar regras de negocio e receber dados das coletas.

A ordem geral de priorizacao seguiu esta logica:

1. Estrutura inicial do projeto e ambiente com Docker.
2. Modelagem do dominio principal e regras de negocio.
3. Comunicacao entre Core e microservico por RabbitMQ.
4. Funcionalidades essenciais de cadastro, autenticacao e consulta.
5. Frontend para interacao com usuarios.
6. Auditoria, monitoramento, backup e documentacao.

Essa priorizacao permitiu que o grupo reduzisse riscos tecnicos primeiro, principalmente nas integracoes entre servicos e na persistencia dos dados.

## 7. Dificuldades encontradas

Uma das principais dificuldades foi a comunicacao, pois todos os integrantes tinham outros afazeres academicos, pessoais e profissionais. Como nem sempre era possivel reunir todo o grupo em horarios fixos, algumas decisoes precisaram ser tomadas de forma assincrona.

Outra dificuldade foi a existencia de varios repositorios. Como o Core, o microservico, o frontend e a observabilidade ficaram separados, nem todas as issues estavam centralizadas no mesmo quadro Kanban. Em um momento, issues do frontend nao foram passadas corretamente para o Kanban principal do Core, o que causou duplicidade de trabalho: duas pessoas chegaram a atuar na mesma tarefa. O problema ocorreu apenas uma vez e foi corrigido pelo grupo por meio de alinhamento e redistribuicao das atividades.

Tambem houve desafios tecnicos relacionados a integracao entre servicos, principalmente por envolver backend, microservico, mensageria, bancos diferentes, frontend e observabilidade. A equipe precisou ajustar o planejamento ao longo do desenvolvimento para lidar com essas dependencias.

## 8. Como as dificuldades foram superadas

As dificuldades de comunicacao foram tratadas com alinhamentos mais objetivos pelo WhatsApp e com reunioes online ou presenciais quando surgiam decisoes importantes. O grupo passou a discutir com mais clareza quem ficaria responsavel por cada tarefa antes de iniciar o desenvolvimento.

A duplicidade causada pelos repositorios separados foi corrigida com revisao do quadro e conversa entre os integrantes. A partir disso, o grupo teve mais cuidado ao verificar se uma tarefa ja estava atribuida ou em andamento antes de iniciar uma nova implementacao.

As dificuldades tecnicas foram superadas por entregas incrementais. Em vez de tentar finalizar todo o sistema de uma vez, o grupo priorizou partes estruturais primeiro, como backend, Docker, mensageria e modelos de dados. Depois avancou para frontend, auditoria, monitoramento, backup e documentacao.

## 9. Metricas de progresso

As metricas coletadas no historico dos repositorios mostram que o desenvolvimento nao ocorreu de forma totalmente uniforme. Houve semanas de baixa atividade, semanas sem commits e semanas de maior concentracao de entregas. Os principais picos ocorreram durante fases de estruturacao do backend, integracao, infraestrutura, observabilidade, CI e documentacao.

Em relacao a commits por semana, o projeto teve maior intensidade nas semanas em que foram implementadas partes estruturais e integracoes importantes. Tambem houve uma semana sem commits, indicando uma pausa no fluxo de desenvolvimento ou baixa atividade registrada no GitHub.

Em relacao a issues, o repositorio principal concentrou a maior parte das tarefas abertas e fechadas.

Sobre o ritmo de entrega aumentou nas fases finais do projeto, principalmente quando o grupo passou a integrar funcionalidades, corrigir problemas, documentar endpoints, criar diagramas de arquitetura, implementar monitoramento e preparar a entrega final.

De forma geral, as metricas indicam um processo com evolção real do produto, mas com concentracao de trabalho em alguns periodos e necessidade de melhorar o acompanhamento formal das tasks.

## 10. Retrospectiva final

Ao final do projeto, o grupo avaliou que a combinacao entre Scrum e Kanban foi adequada para a realidade da equipe. O Kanban ajudou a visualizar o fluxo das tarefas, enquanto as praticas inspiradas em Scrum ajudaram na divisao de responsabilidades, revisao de prioridades e organizacao das entregas.

O principal ponto positivo foi a preocupacao inicial com arquitetura. Priorizar o backend e as integracoes permitiu construir uma base mais consistente para o restante do sistema. Outro ponto positivo foi a capacidade do grupo de se adaptar quando surgiram dificuldades, como problemas de comunicacao, repositorios separados e ajustes nas prioridades.

Como ponto negativo, o grupo identificou que a falta de reunioes fixas dificultou o acompanhamento constante do progresso. Alem disso, a separacao em varios repositorios exigia mais disciplina na gestao das issues e do quadro Kanban. A duplicidade pontual de tarefa mostrou que o processo precisava de melhor sincronizacao entre os repositorios.

Para projetos futuros, o grupo recomenda:

- definir uma reuniao curta semanal, mesmo que online;
- centralizar todas as tasks em um unico board;
- associar cada pull request a uma issue;
- fechar issues no momento em que a funcionalidade for entregue;
- revisar o Kanban periodicamente;
- manter uma documentacao minima de decisoes tecnicas;
- distribuir melhor o conhecimento entre os integrantes para reduzir dependencia de uma unica pessoa por modulo.

## 11. Conclusao

O processo de desenvolvimento do Coleta Premiada refletiu a realidade do grupo: uma metodologia hibrida, flexivel e adaptada a disponibilidade dos integrantes. Apesar de nao seguir Scrum de forma formal, o grupo utilizou praticas importantes de planejamento, divisao de tarefas, revisao e acompanhamento visual por Kanban.

As principais dificuldades estiveram relacionadas a comunicacao, disponibilidade e organizacao entre repositorios. Ainda assim, o grupo conseguiu evoluir o sistema de forma incremental, entregando backend, microservico, frontend, observabilidade, auditoria, backup e documentacao.

Como aprendizado final, o grupo percebeu que o uso de um quadro Kanban e essencial, mas precisa estar sempre atualizado e centralizado para evitar duplicidade, perda de rastreabilidade e divergencia entre o trabalho realizado e o trabalho registrado.