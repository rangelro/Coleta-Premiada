# Regras de Negócio — Coleta Premiada

---

## 1. Cadastro e Contas

| ID | Regra | Descrição |
|----|-------|-----------|
| RN01 | Autocadastro como morador | Qualquer pessoa pode se cadastrar no sistema, mas sempre será criada com perfil **morador**. Perfis administrativos só podem ser criados por um Gestor. |
| RN02 | Exclusão lógica | Usuários e imóveis nunca são excluídos fisicamente do banco de dados — são marcados como `ativo=False` (soft delete). |
| RN03 | Gestor não pode se autoexcluir | Um Gestor não pode excluir a própria conta. |
| RN04 | Gestor não cria Gerente Geral | Um Gestor não pode criar ou promover outro usuário ao perfil **gerente_geral**. |

---

## 2. Imóveis

| ID | Regra | Descrição |
|----|-------|-----------|
| RN05 | Titular obrigatório | Todo imóvel deve ter um **titular** com perfil **morador**. |
| RN06 | Múltiplos moradores | Um imóvel pode ter vários moradores vinculados, mas apenas um titular. |
| RN07 | Titular não pode ser removido | O titular do imóvel não pode ser desvinculado (apenas moradores adicionais podem). |
| RN08 | Cidade ativa obrigatória | O imóvel deve pertencer a uma cidade cadastrada e ativa no sistema. |
| RN09 | Geocodificação automática | Ao cadastrar um imóvel sem coordenadas, o sistema tenta geocodificar automaticamente o endereço via OpenStreetMap (Nominatim), respeitando limite de 1 requisição/segundo. |
| RN10 | Sincronização automática com microsserviço | Ao criar ou alterar um imóvel, uma mensagem é publicada automaticamente na fila RabbitMQ `imoveis` para replicação no microsserviço de coleta. |

---

## 3. Programas e Ciclos

| ID | Regra | Descrição |
|----|-------|-----------|
| RN11 | Programa por cidade | Cada programa pertence a exatamente uma cidade. |
| RN12 | Escopo do Gestor | Um Gestor só pode criar/editar programas na cidade à qual está vinculado. |
| RN13 | Gerente Geral não opera programas | O perfil **gerente_geral** está explicitamente proibido de criar, editar ou excluir programas, regras, ciclos e consolidações. |
| RN14 | Ciclo aberto para coleta | Apenas ciclos com status **aberto** permitem o registro de novas coletas para fins de consolidação. |

---

## 4. Pontuação

| ID | Regra | Descrição |
|----|-------|-----------|
| RN15 | Cálculo de pontos | `pontuação = peso_kg × pontos_por_kg` (constante configurável global). |
| RN16 | Constante de pontuação global | O valor de `pontos_por_kg` é único para todo o sistema e editável apenas pelo perfil **supervisor**. |
| RN17 | Pontuação por peso total | A pontuação é calculada com base no peso total da coleta, sem distinção por tipo de material reciclado. |
| RN18 | Deduplicação de coletas | Cada coleta possui um identificador único do microsserviço (`id_microservico`). Mensagens duplicadas na fila RabbitMQ são ignoradas silenciosamente. |

---

## 5. Consolidação e Desconto IPTU

| ID | Regra | Descrição |
|----|-------|-----------|
| RN19 | Consolidação explícita | A consolidação é uma ação manual disparada pelo Gestor — não ocorre automaticamente. |
| RN20 | Mínimo para benefício | Imóveis com pontuação abaixo do `minimo_para_beneficio` configurado no programa são excluídos do desconto. |
| RN21 | Cálculo do desconto | `desconto = pontos_acumulados / pontos_por_real` (regra do programa). |
| RN22 | Teto máximo de 40% | O desconto de IPTU é limitado a **40%** por ciclo, independentemente da pontuação acumulada. |
| RN23 | Teto configurável | O programa pode definir um `desconto_maximo` próprio (valor padrão: 40%). |
| RN24 | Fechamento do ciclo | Após a consolidação, o ciclo é fechado (`status = fechado`), impedindo novas coletas vinculadas. |
| RN25 | Acumulação entre ciclos | O programa pode permitir ou proibir a acumulação de pontos entre ciclos (`permite_acumulo_ciclos`). |

---

## 6. Coleta

| ID | Regra | Descrição |
|----|-------|-----------|
| RN26 | Offline-first | Coletas realizadas no aplicativo mobile são salvas primeiro no banco local (SQLite) e depois sincronizadas com o servidor. |
| RN27 | Idempotência offline | Cada coleta offline possui um `offline_id` (UUID) que garante que a mesma coleta não seja duplicada ao ser sincronizada. |
| RN28 | Tipo de material não registrado | O sistema registra apenas o peso total da coleta — não há separação por tipo de material (plástico, papel, vidro, metal). |
| RN29 | Foto opcional | O registro fotográfico do material coletado é opcional. |

---

## 7. Contestações

| ID | Regra | Descrição |
|----|-------|-----------|
| RN30 | Abertura pelo morador | Apenas o morador pode abrir uma contestação, e somente sobre coletas realizadas em seus próprios imóveis. |
| RN31 | Motivo mínimo | A contestação deve conter um motivo com no mínimo 10 caracteres. |
| RN32 | Análise pelo Gestor | Apenas o perfil **gestor** pode analisar e responder contestações. |
| RN33 | Status possíveis | Uma contestação pode estar nos status: `aberta`, `em_analise`, `aceita` ou `negada`. |

---

## 8. Visibilidade e Escopo de Dados

| ID | Regra | Descrição |
|----|-------|-----------|
| RN34 | Morador vê apenas seus dados | O morador visualiza exclusivamente dados dos imóveis aos quais está vinculado (como titular ou morador adicional). |
| RN35 | Gestor e Supervisor por cidade | Gestor e Supervisor visualizam apenas dados da cidade à qual estão vinculados. |
| RN36 | Gerente Geral irrestrito | O Gerente Geral tem acesso de leitura a dados de todas as cidades. |

---

## 9. Auditoria

| ID | Regra | Descrição |
|----|-------|-----------|
| RN37 | Auditoria automática | Todas as operações de criação, alteração e exclusão em modelos principais são registradas automaticamente em log de auditoria. |
| RN38 | Auditoria de consulta | Operações de leitura em endpoints sensíveis (usuários, imóveis, programas, coletas) também são auditadas. |
| RN39 | Dados da auditoria | Cada registro de auditoria contém: usuário, timestamp, operação, tabela, ID do objeto, estado anterior/posterior (JSON), IP de origem e endpoint. |
| RN40 | Acesso restrito | Apenas o perfil **gestor** pode acessar e exportar logs de auditoria. |
| RN41 | Retenção de logs | Logs de auditoria são mantidos por 90 dias no PostgreSQL (limpeza automatizada por script de manutenção). |

---

## 10. Sincronização e Mensageria

| ID | Regra | Descrição |
|----|-------|-----------|
| RN42 | Mensagens persistentes | Mensagens RabbitMQ são marcadas como persistentes para garantir entrega mesmo em caso de falha do broker. |
| RN43 | Sem DLQ | Mensagens com falha de processamento são rejeitadas sem reencaminhamento (não há Dead Letter Queue configurada). |
| RN44 | Sincronização cross-service | Core → Microsserviço: fila `imoveis`. Microsserviço → Core: fila `coletas`. A comunicação é unidirecional e assíncrona. |

---

## 11. Monitoramento

| ID | Regra | Descrição |
|----|-------|-----------|
| RN45 | Retenção de métricas | Prometheus retém métricas por 30 dias. |
| RN46 | Alertas sem notificação | Alertas são disparados na interface do Prometheus mas não enviam notificações externas (Alertmanager não configurado). |
| RN47 | Fuso horário brasileiro | Dashboards do Grafana utilizam o fuso `America/Fortaleza` (UTC-3). |
