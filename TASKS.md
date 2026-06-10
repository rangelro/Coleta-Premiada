# Tarefas — Entrega 2 · Coleta Premiada

> Escala de story points (Fibonacci): 1 · 2 · 3 · 5 · 8 · 13 · 21  
> Total estimado: **178 SP**

---

## Geolocalização — Core

### [GEO-CORE-1] Adicionar campos de coordenadas ao model Imovel no Core
**Story Points: 2**

Adicionar os campos `latitude` e `longitude` (DecimalField, max_digits=9, decimal_places=6, null=True) ao model `Imovel` em `core/program/models.py`. Criar e aplicar a migration correspondente no PostgreSQL.

---

### [GEO-CORE-2] Geocodificação automática de imóveis no Core via Nominatim
**Story Points: 8**

Instalar `geopy` no Core. Implementar função de geocodificação (logradouro + número + bairro + cidade + CEP → lat/lng) usando Nominatim/OpenStreetMap. Disparar assincronamente via Celery no `post_save` signal do model `Imovel` quando lat/lng estiverem nulos. Marcar imóveis sem resultado com flag `geocodificacao_falhou=True` para reprocessamento manual. Respeitar o rate limit de 1 req/s do Nominatim.

---

### [GEO-CORE-3] Script de geocodificação em batch para imóveis existentes
**Story Points: 5**

Criar management command Django (`python manage.py geocodificar_imoveis`) que geocodifica todos os imóveis com `latitude=None` em lote, respeitando o rate limit de 1 req/s do Nominatim e exibindo progresso. Logar erros por imóvel sem interromper o batch. Incluir opção `--dry-run` para simulação.

---

### [GEO-CORE-4] Incluir coordenadas no evento RabbitMQ de sincronização Core → MS
**Story Points: 3**

No Core, ao publicar o evento de criação/atualização de imóvel na fila `imoveis` do RabbitMQ, incluir os campos `latitude` e `longitude` no payload JSON. Atualizar o consumer do MS para ler e persistir essas coordenadas. Garantir compatibilidade com imóveis que ainda não foram geocodificados (campos nullable).

---

## Geolocalização — Microserviço (MS)

### [GEO-MS-1] Adicionar campo GeoJSON e índice 2dsphere ao model Imovel no MS
**Story Points: 5**

No projeto cp-collection-ms (Django/MongoDB), adicionar campo `location` no model `Imovel` usando formato GeoJSON Point: `{ type: "Point", coordinates: [longitude, latitude] }`. Criar índice `2dsphere` nesse campo via migration. Atualizar o consumer RabbitMQ para preencher o campo `location` a partir de latitude/longitude recebidos. Coordenadas podem ser nulas (imóveis sem geocodificação).

---

### [GEO-MS-2] Criar endpoint GET /api/imoveis/proximos no MS
**Story Points: 8**

Criar endpoint `GET /api/imoveis/proximos?lat=X&lng=Y&raio=200` que usa query MongoDB `$near` com `$maxDistance=200` (metros) no campo `location`. Retornar imóveis ordenados por distância crescente, incluindo: distância calculada, logradouro, numero, bairro, complemento, id_externo, elegivel e flag `coletado_hoje` (se já houve coleta do coletor autenticado no dia). Excluir imóveis sem coordenadas do resultado. Parâmetros adicionais opcionais: `logradouro` (filtro por nome de rua) e `bairro` (filtro por bairro).

---

## Geolocalização — App

### [GEO-APP-1] Implementar hook useLocation no app com intervalo de 10 segundos
**Story Points: 3**

Criar `hooks/use-location.ts` usando `expo-location`. Solicitar permissão de localização ao iniciar. Rastrear posição com accuracy `Balanced` e intervalo de 10 segundos enquanto o app está em foreground. Pausar rastreamento ao entrar em background. Retornar `{ latitude, longitude, error, loading }`. Tratar permissão negada com mensagem explicativa ao usuário.

---

### [GEO-APP-2] Implementar armazenamento offline dos imóveis da cidade no app
**Story Points: 13**

Criar mecanismo para baixar e armazenar localmente todos os imóveis da cidade usando `expo-sqlite`. Criar tabela local `imoveis` com todos os campos relevantes, incluindo lat/lng. Sincronizar com o MS no login e quando houver conexão disponível. Adicionar tela/indicador de status de sincronização offline. A query de proximidade deve rodar localmente contra o SQLite (fórmula haversine em JS) quando o app estiver offline.

---

### [GEO-APP-3] Criar tela de mapa com pins dos imóveis próximos
**Story Points: 13**

Instalar `react-native-maps` e criar tela `app/mapa/index.tsx`. Exibir mapa centrado na posição atual do coletor (atualizado a cada 10s). Mostrar pins dos imóveis num raio de 200m com cores diferenciadas: verde (não visitado), cinza (visitado hoje), vermelho (inelegível). Ao tocar em um pin, exibir card com endereço, distância e botão "Iniciar Coleta". Botão de alternância mapa/lista na mesma tela. Funcionar com dados offline do SQLite local.

---

### [GEO-APP-4] Criar listagem de imóveis próximos com filtro por rua e bairro
**Story Points: 8**

Refatorar a aba de coleta (`app/(tabs)/coletar.tsx`) para exibir lista de imóveis próximos (raio 200m) ordenados por distância. Cada item deve mostrar: distância em metros, logradouro e número, bairro e status do dia (não visitado / visitado / inelegível). Incluir filtros "Mesma rua" (filtra pelo logradouro atual via reverse geocoding) e "Mesmo bairro". Tocar no item inicia o fluxo de coleta. Lista deve funcionar offline com dados do SQLite local.

---

## LLM — Relatórios

### [LLM-1] Criar serviço de integração com LLM no Core para geração de relatórios
**Story Points: 8**

No Core (Django), criar módulo `core/reports/llm_service.py` que integra com a API da Claude (Anthropic SDK). O serviço deve: (1) receber um tipo de relatório e período como parâmetros; (2) consultar os dados relevantes do banco (coletas, pontuações, participação, imóveis); (3) montar um prompt estruturado com os dados em JSON; (4) enviar ao LLM e retornar o relatório em texto narrativo; (5) usar prompt caching (`cache_control`) para reduzir custos nos prompts de sistema. Modelo padrão: `claude-sonnet-4-6`.

---

### [LLM-2] Criar endpoints de geração de relatórios com LLM no Core
**Story Points: 5**

Criar endpoints em `core/reports/`: `POST /api/reports/generate` com body `{ tipo: "participacao"|"impacto"|"ranking"|"auditoria", periodo: { inicio, fim }, programa_id? }`. O endpoint aciona o LLM e retorna o relatório textual gerado. Adicionar `GET /api/reports/history` para listar relatórios gerados anteriormente (salvar no banco). Apenas gestores podem acessar. A resposta deve incluir: relatório em texto, timestamp, tipo, período e tokens utilizados.

---

## Autenticação OAuth

### [AUTH-1] Integrar autenticação OAuth via SUAP no Core
**Story Points: 8**

Integrar login via SUAP OAuth2 no Core usando `django-allauth` ou `python-social-auth`. Configurar: client_id, client_secret, URL de callback, mapeamento de campos (matrícula, nome, email). O token JWT do sistema deve ser emitido após autenticação OAuth bem-sucedida. Adaptar endpoint `/auth/login` para aceitar o fluxo OAuth além do login local. Documentar variáveis de ambiente necessárias no `.env.example`.

---

## Auditoria de Banco de Dados

### [AUDIT-1] Implementar sistema de auditoria de banco de dados no Core
**Story Points: 8**

Criar model `AuditLog` com campos: `id`, `timestamp`, `usuario_id`, `usuario_email`, `operacao` (INSERT/UPDATE/DELETE/SELECT), `tabela`, `objeto_id`, `dados_antes` (JSON), `dados_depois` (JSON), `ip_origem`, `endpoint`. Implementar via Django signals (`post_save`, `post_delete`) nos models principais: Imovel, Coleta, RegistroColeta, Programa, Usuario. Para consultas de leitura relevantes, registrar via middleware. Criar índices em `timestamp`, `usuario_id` e `tabela`.

---

### [AUDIT-2] Implementar auditoria de operações no MS (MongoDB)
**Story Points: 5**

Implementar auditoria no MS usando Django signals (`post_save`, `post_delete`) nos models `Coleta` e `Imovel`. Criar coleção `audit_logs` com campos: `timestamp`, `usuario_matricula`, `operacao`, `colecao`, `documento_id`, `dados_antes`, `dados_depois`. Criar índice TTL de 90 dias para limpeza automática de logs antigos. Middleware para capturar `ip_origem` e `endpoint` no request context.

---

### [AUDIT-3] Criar endpoints e interface de consulta de auditoria no Core
**Story Points: 5**

Criar `GET /api/audit/logs` com filtros: `usuario_id`, `tabela`, `operacao`, `data_inicio`, `data_fim`, `objeto_id`. Paginação obrigatória (max 100 por página). Apenas gestor pode acessar. Criar `GET /api/audit/logs/export?formato=csv` para exportação. Esses endpoints atendem ao requisito de "interfaces para geração de relatórios de auditoria" exigido pelo guia do projeto.

---

## Backup Automático

### [BACKUP-1] Configurar backup automático do PostgreSQL (Core)
**Story Points: 3**

Adicionar serviço `db-backup` ao `docker-compose.yml` do Core usando `pg_dump` em cron diário (`0 2 * * *`). Configurar retenção de 7 backups diários + 4 semanais, com destino em volume Docker `/backups/postgres`. Incluir script de restore documentado. Documentar variáveis de ambiente no `.env.example`.

---

### [BACKUP-2] Configurar backup automático do MongoDB (MS)
**Story Points: 3**

Adicionar serviço `mongo-backup` ao `docker-compose.yml` do MS usando `mongodump` em cron diário (`0 3 * * *`). Compactar dumps com gzip, reter 7 backups, salvar em volume `/backups/mongo`. Incluir script de restore com `mongorestore`. Documentar processo de recuperação no README do MS.

---

## Monitoramento e Alertas

### [MON-1] Configurar stack de monitoramento Prometheus + Grafana
**Story Points: 8**

Criar `docker-compose.monitoring.yml` com: `prometheus`, `grafana`, `postgres_exporter`, `mongodb_exporter` e `node_exporter`. Configurar `prometheus.yml` com scrape_configs para todos os exporters. Persistir dados do Grafana em volume. Porta padrão Grafana: 3000. Documentar credenciais padrão e acesso no README.

---

### [MON-2] Criar dashboard Grafana e configurar alertas críticos
**Story Points: 8**

Criar dashboard Grafana com painéis: conexões ativas PostgreSQL, queries lentas (pg_stat_statements), uso de disco, locks longos, taxa de erros HTTP, coletas por hora, status da fila RabbitMQ. Configurar alertas para: conexões PG > 80% do max_connections, query com duração > 5s, disco > 80%, fila RabbitMQ > 1000 mensagens pendentes. Exportar dashboard como JSON e versionar no repositório.

---

### [MON-3] Criar scripts de manutenção automatizada do banco de dados
**Story Points: 5**

Criar scripts em `scripts/maintenance/`: (1) `vacuum_analyze.sh` — VACUUM ANALYZE nas tabelas principais do PostgreSQL; (2) `reindex.sh` — REINDEX nas tabelas com alto volume de updates; (3) `cleanup_logs.sh` — apaga AuditLogs com mais de 90 dias no PostgreSQL; (4) `cleanup_mongo_logs.sh` — limpeza equivalente no MongoDB (complementar ao TTL index). Adicionar como cron jobs no docker-compose. Documentar periodicidade recomendada.

---

## CI/CD

### [CICD-1] Criar workflow GitHub Actions de CI (testes e lint)
**Story Points: 5**

Criar `.github/workflows/ci.yml` que executa em cada push/PR para `develop` e `master`. Jobs: (1) `test-core` — sobe PostgreSQL + RabbitMQ como services e roda `pytest`; (2) `test-ms` — sobe MongoDB + RabbitMQ e roda testes do MS; (3) `lint` — roda `flake8` e `black --check` em ambos os backends; (4) `test-app` — roda `expo lint` e `tsc --noEmit`. Falha em qualquer job bloqueia o merge.

---

### [CICD-2] Criar workflow GitHub Actions de CD (build e deploy das imagens Docker)
**Story Points: 5**

Criar `.github/workflows/cd.yml` que executa apenas em push para `master`. Jobs: (1) build e push das imagens Docker do Core e do MS para o GitHub Container Registry (ghcr.io); (2) deploy via SSH para servidor de produção usando GitHub Secrets. Usar cache de layers Docker para acelerar builds. Versionar imagens com SHA do commit e tag `latest`.

---

## Documentação

### [DOC-1] Escrever READMEs dos três projetos
**Story Points: 3**

Atualizar/criar `README.md` nos três repositórios. Cada README deve conter: (a) propósito do sistema e papel na arquitetura; (b) stack tecnológica com versões; (c) pré-requisitos; (d) passo a passo de instalação local com Docker; (e) variáveis de ambiente (referência ao `.env.example`); (f) como rodar os testes; (g) link para a Wiki. O README do Core deve incluir diagrama ASCII da arquitetura de serviços.

---

### [DOC-2] Documentar todos os endpoints com entrada/saída detalhada
**Story Points: 5**

Produzir documento detalhado de todos os endpoints dos três serviços (Core + MS + novos). Para cada endpoint: método HTTP, URL, autenticação necessária, parâmetros de query, body de request (com tipos e exemplos JSON), body de response (com tipos e exemplos), códigos de status possíveis e erros. Atualizar o `ENDPOINTS.md` do app e criar equivalente nos backends. Esse documento também alimenta a Wiki.

---

### [DOC-3] Produzir diagramas de arquitetura no Modelo C4 (Contexto, Container, Componentes)
**Story Points: 8**

Criar os três níveis do Modelo C4: (1) Diagrama de Contexto — sistema e atores externos (gestor, supervisor, coletor, SUAP, Nominatim, LLM, RabbitMQ); (2) Diagrama de Containers — Core (Django+PG), MS (Django+Mongo), App (React Native), RabbitMQ, Grafana+Prometheus; (3) Diagrama de Componentes — detalhamento interno do Core e do MS. Usar PlantUML ou draw.io, versionar fontes no repositório e exportar como PNG. Publicar na Wiki.

---

### [DOC-4] Criar visões arquiteturais funcionais e de desenvolvimento
**Story Points: 5**

Produzir: (a) Visão Funcional — diagrama de fluxo de dados mostrando como uma coleta percorre todo o sistema (app → MS → RabbitMQ → Core → LLM) e o fluxo de geolocalização (GPS → SQLite local → MS → resposta); (b) Visão de Desenvolvimento — estrutura de diretórios relevante, convenções de branch (Git flow adotado), como rodar localmente para desenvolvimento, como adicionar novos endpoints. Publicar na Wiki do repositório principal.

---

### [DOC-5] Publicar Wiki completa no repositório GitHub
**Story Points: 5**

Criar e popular a Wiki do GitHub com as seções: (a) Escopo do sistema; (b) Funcionalidades — requisitos funcionais (RF) e de qualidade (RNF); (c) Diagramas auxiliares — classe e casos de uso; (d) Modelo C4; (e) Auditoria, Monitoramento e Backup — como foram implementados, configurações padrão dos administradores, como consultar logs, como restaurar backup, como acessar o Grafana. Cada seção deve ser uma página separada com sumário principal linkando todas.

---

### [DOC-6] Escrever Relatório de Processo de Software
**Story Points: 3**

Produzir documento PDF descrevendo: o processo de software adotado (Scrum/Kanban/etc.); como as sprints/iterações foram conduzidas; cerimônias realizadas; como os requisitos foram priorizados; dificuldades encontradas e como foram superadas; métricas de progresso (commits por semana, issues fechadas, velocity). Deve refletir o processo real usado pelo grupo. Incluir retrospectiva final.

---

## Infraestrutura

### [INFRA-1] Revisar e consolidar docker-compose de todos os serviços
**Story Points: 5**

Revisar os `docker-compose.yml` existentes no Core e no MS. Garantir que todos os serviços estejam configurados: Core (Django + Celery + PostgreSQL + Redis), MS (Django + MongoDB), RabbitMQ, Grafana, Prometheus, exporters e serviços de backup. Criar `docker-compose.override.yml` para ambiente de desenvolvimento (volumes de código montados, DEBUG=true, portas expostas). Verificar que um único `docker compose up` sobe todo o sistema funcional.

---

## Resumo por área

| Área | Tarefas | Story Points |
|------|---------|-------------|
| Geolocalização — Core | 4 | 18 SP |
| Geolocalização — MS | 2 | 13 SP |
| Geolocalização — App | 4 | 37 SP |
| LLM — Relatórios | 2 | 13 SP |
| Autenticação OAuth | 1 | 8 SP |
| Auditoria de Banco | 3 | 18 SP |
| Backup Automático | 2 | 6 SP |
| Monitoramento e Alertas | 3 | 21 SP |
| CI/CD | 2 | 10 SP |
| Documentação | 6 | 29 SP |
| Infraestrutura | 1 | 5 SP |
| **Total** | **30** | **178 SP** |
