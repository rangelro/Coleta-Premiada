# Funcionalidades do Sistema — Coleta Premiada

## 1. Autenticação e Conta

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F01 | Autocadastro como morador (e-mail/senha) | Morador | Alta |
| F02 | Login com e-mail e senha | Todos (exceto Coletor) | Alta |
| F03 | Login com Google OAuth | Morador | Média |
| F04 | Login com matrícula e senha | Coletor | Alta |
| F05 | Recuperação de sessão (token persistente) | Coletor | Alta |
| F06 | Visualizar e editar perfil próprio | Morador, Coletor | Média |
| F07 | Exclusão lógica da própria conta | Morador | Baixa |

---

## 2. Gestão de Imóveis

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F08 | Cadastrar imóvel para participar do programa | Morador | Alta |
| F09 | Visualizar dados do próprio imóvel | Morador | Alta |
| F10 | Listar imóveis do município | Supervisor, Gestor | Alta |
| F11 | Cadastrar imóvel manualmente | Supervisor, Gestor | Alta |
| F12 | Editar dados do imóvel | Supervisor, Gestor | Alta |
| F13 | Vincular morador a imóvel | Supervisor, Gestor | Média |
| F14 | Desvincular morador de imóvel | Supervisor, Gestor | Média |
| F15 | Buscar imóvel por endereço, número IPTU ou QR Code | Coletor | Alta |
| F16 | Localizar imóveis próximos em mapa | Coletor | Alta |

---

## 3. Coleta de Resíduos

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F17 | Registrar coleta (fluxo completo: identificar → pesar → fotografar → confirmar) | Coletor | Alta |
| F18 | Identificar imóvel por número IPTU | Coletor | Alta |
| F19 | Identificar imóvel por QR Code | Coletor | Média |
| F20 | Identificar imóvel por endereço | Coletor | Média |
| F21 | Registrar peso da coleta (kg) | Coletor | Alta |
| F22 | Fotografar material coletado (opcional) | Coletor | Média |
| F23 | Adicionar observações à coleta | Coletor | Baixa |
| F24 | Operar offline (coleta salva localmente e sincronizada depois) | Coletor | Alta |
| F25 | Sincronizar coletas pendentes manualmente | Coletor | Alta |
| F26 | Sincronização automática ao recuperar conectividade | Coletor | Alta |
| F27 | Registrar coleta manualmente (via web) | Supervisor, Gestor | Média |

---

## 4. Histórico e Consultas

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F28 | Visualizar histórico de coletas do próprio imóvel | Morador | Alta |
| F29 | Visualizar histórico de coletas realizadas (filtros: hoje/ontem/semana) | Coletor | Alta |
| F30 | Visualizar detalhe de uma coleta | Coletor | Média |
| F31 | Visualizar histórico geral de coletas (filtros por programa, período) | Supervisor, Gestor | Alta |
| F32 | Visualizar fotos de evidência de coleta | Morador, Supervisor, Gestor | Média |

---

## 5. Pontuação e Benefícios

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F33 | Visualizar total de pontos acumulados | Morador | Alta |
| F34 | Visualizar saldo de descontos IPTU por ciclo | Morador | Alta |
| F35 | Consultar programa ativo e suas regras | Morador | Média |
| F36 | Configurar constante de pontuação (pontos por kg) | Supervisor | Alta |
| F37 | Visualizar benefícios gerados por imóvel | Supervisor, Gestor | Alta |

---

## 6. Programas e Ciclos

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F38 | Criar programa de reciclagem | Gestor | Alta |
| F39 | Editar programa (nome, datas, status, desconto máximo) | Gestor | Alta |
| F40 | Configurar regras do programa (pontos por real, mínimo para benefício, acumulação entre ciclos) | Gestor | Alta |
| F41 | Criar ciclo (mensal, semestral, anual, personalizado) | Gestor, Supervisor | Alta |
| F42 | Listar ciclos por programa | Supervisor, Gestor | Alta |
| F43 | Visualizar detalhes do programa e regras | Todos | Média |

---

## 7. Consolidação (Desconto IPTU)

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F44 | Executar consolidação de ciclo (calcular descontos) | Gestor | Alta |
| F45 | Visualizar histórico de consolidações realizadas | Gestor, Supervisor | Alta |
| F46 | Visualizar detalhes de uma consolidação | Gestor, Supervisor | Média |

---

## 8. Contestações

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F47 | Abrir contestação sobre registro de coleta | Morador | Média |
| F48 | Listar contestações (filtro por status) | Morador, Gestor | Média |
| F49 | Analisar e responder contestação (status: em análise, aceita, negada) | Gestor | Média |

---

## 9. Relatórios

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F50 | Visualizar dashboard executivo (KPIs, gráficos, ranking) | Gestor | Alta |
| F51 | Relatório de participação (coletas e pontos por imóvel) | Supervisor, Gestor | Média |
| F52 | Relatório de coletas por ciclo (totais agrupados) | Supervisor, Gestor | Média |
| F53 | Relatório de ranking de imóveis por pontuação | Supervisor, Gestor | Média |
| F54 | Relatório de impacto (totais agregados do programa) | Supervisor, Gestor | Média |
| F55 | Gerar relatório narrativo via IA (participação, impacto, ranking, auditoria) | Gestor | Baixa |
| F56 | Visualizar histórico de relatórios gerados | Gestor | Baixa |

---

## 10. Gestão de Usuários e Papéis

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F57 | Listar usuários do município (filtros por perfil, status) | Gestor | Alta |
| F58 | Criar usuário (qualquer perfil) | Gestor | Alta |
| F59 | Ativar/desativar usuário | Gestor | Alta |
| F60 | Gerenciar papéis personalizados (criar, editar, atribuir, remover) | Gestor | Média |
| F61 | Gerenciar cidades (criar, editar) | Gerente Geral | Alta |

---

## 11. Auditoria

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F62 | Visualizar logs de auditoria (filtros por usuário, tabela, operação) | Gestor | Média |
| F63 | Exportar logs de auditoria em CSV | Gestor | Baixa |

---

## 12. Sincronização e Offline (Coletor)

| ID | Funcionalidade | Ator | Prioridade |
|----|---------------|------|------------|
| F64 | Visualizar status de sincronização (pendentes, sincronizadas hoje) | Coletor | Alta |
| F65 | Sincronizar coletas pendentes em lote | Coletor | Alta |
| F66 | Baixar mapas offline para uso sem conectividade | Coletor | Média |
| F67 | Visualizar mapa com imóveis offline | Coletor | Média |

---

## 13. Monitoramento (Observabilidade)

| ID | Funcionalidade | Responsável | Prioridade |
|----|---------------|-------------|------------|
| F68 | Monitorar métricas do PostgreSQL (conexões, queries lentas) | Equipe Técnica | Alta |
| F69 | Monitorar métricas do MongoDB (conexões, operações) | Equipe Técnica | Alta |
| F70 | Monitorar taxa de erros HTTP (5xx) | Equipe Técnica | Alta |
| F71 | Monitorar latência HTTP (p50, p95, p99) | Equipe Técnica | Alta |
| F72 | Monitorar fila RabbitMQ (mensagens prontas, não entregues) | Equipe Técnica | Alta |
| F73 | Monitorar uso de CPU e memória dos containers | Equipe Técnica | Alta |
| F74 | Alertas: conexões PostgreSQL alto, queries lentas, disco cheio, fila acumulada | Equipe Técnica | Alta |
