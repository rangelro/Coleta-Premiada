# Histórias de Usuário — Coleta Premiada

---

## Autenticação e Cadastro

### HU01 — Cadastro como Morador
**Como** morador  
**Quero** me cadastrar no sistema com e-mail e senha  
**Para** aderir ao programa de reciclagem e começar a acumular pontos para desconto no IPTU

**Critérios de Aceitação:**
- O cadastro cria automaticamente o perfil "morador"
- Deve ser possível cadastrar também via Google OAuth
- Após o cadastro, o usuário é redirecionado ao dashboard do morador

### HU02 — Login com Matrícula (Coletor)
**Como** coletor  
**Quero** fazer login no aplicativo mobile com minha matrícula e senha  
**Para** acessar minhas funcionalidades de campo mesmo em áreas com conectividade limitada

**Critérios de Aceitação:**
- A sessão deve persistir no dispositivo (SecureStore)
- O token deve ser renovado automaticamente quando possível

---

## Imóveis

### HU03 — Cadastro de Imóvel
**Como** morador  
**Quero** cadastrar meu imóvel informando endereço, inscrição imobiliária e número de moradores  
**Para** que o imóvel seja elegível para participar do programa de coleta seletiva

**Critérios de Aceitação:**
- A cidade deve estar cadastrada no sistema
- O morador se torna titular do imóvel automaticamente
- O sistema deve tentar geocodificar o endereço automaticamente

### HU04 — Localização de Imóvel pelo Coletor
**Como** coletor  
**Quero** localizar imóveis próximos à minha localização atual no mapa  
**Para** planejar a rota de coleta e identificar quais imóveis estão elegíveis

**Critérios de Aceitação:**
- Deve ser possível buscar por número IPTU, QR Code ou endereço
- Deve funcionar offline com dados previamente baixados

---

## Coleta

### HU05 — Registro de Coleta em Campo
**Como** coletor  
**Quero** registrar uma coleta seguindo as etapas: identificar imóvel, pesar, fotografar (opcional) e confirmar  
**Para** que o morador receba os pontos correspondentes ao peso dos materiais coletados

**Critérios de Aceitação:**
- O peso deve ser registrado em kg com suporte a decimais
- A foto é opcional
- A coleta deve ser salva offline se não houver conectividade
- Após a confirmação, o código da coleta deve ser exibido

### HU06 — Sincronização de Coletas Offline
**Como** coletor  
**Quero** que as coletas realizadas offline sejam sincronizadas automaticamente quando houver conectividade  
**Para** não perder nenhum registro e garantir que os moradores recebam seus pontos corretamente

**Critérios de Aceitação:**
- Sincronização automática ao detectar conectividade
- Possibilidade de sincronização manual
- Indicador visual do status de sincronização de cada coleta

---

## Programas e Gestão

### HU07 — Criação de Programa de Reciclagem
**Como** gestor  
**Quero** criar um programa de reciclagem definindo nome, período de vigência e regras de pontuação  
**Para** estruturar a iniciativa de coleta seletiva no meu município

**Critérios de Aceitação:**
- Devo poder configurar: pontos por real, mínimo para benefício e acumulação entre ciclos
- O programa fica vinculado à minha cidade automaticamente

### HU08 — Execução de Consolidação
**Como** gestor  
**Quero** executar a consolidação de um ciclo para calcular os descontos de IPTU  
**Para** que os moradores recebam os benefícios acumulados no período

**Critérios de Aceitação:**
- A consolidação considera apenas coletas em ciclos abertos e não consolidadas
- Imóveis abaixo do mínimo para benefício são excluídos
- O desconto máximo é limitado a 40%
- Após a consolidação, o ciclo é fechado

---

## Acompanhamento

### HU09 — Visualização de Pontos e Benefícios
**Como** morador  
**Quero** visualizar meus pontos acumulados e os descontos de IPTU gerados por ciclo  
**Para** acompanhar meu engajamento no programa e planejar os próximos descartes

### HU10 — Dashboard Executivo
**Como** gestor  
**Quero** acessar um dashboard com KPIs, gráficos de participação e ranking de imóveis  
**Para** monitorar o desempenho do programa e tomar decisões baseadas em dados

**Critérios de Aceitação:**
- KPIs: total de coletas, total de pontos, imóveis participantes, descontos gerados
- Gráfico de coletas por ciclo
- Ranking top 10 de imóveis por pontuação
- Alertas de contestações pendentes

---

## Contestações

### HU11 — Abertura de Contestação
**Como** morador  
**Quero** contestar um registro de coleta que considero incorreto  
**Para** que o gestor analise e corrija caso necessário

**Critérios de Aceitação:**
- A contestação deve ter motivo com mínimo de 10 caracteres
- Só posso contestar coletas dos meus próprios imóveis
- O status da contestação deve ser atualizado após análise do gestor

---

## Relatórios

### HU12 — Geração de Relatório Narrativo
**Como** gestor  
**Quero** gerar um relatório narrativo automático sobre a participação e impacto do programa  
**Para** compartilhar com a administração municipal e a comunidade

**Critérios de Aceitação:**
- Tipos de relatório: participação, impacto, ranking, auditoria
- O relatório é gerado por IA com base nos dados reais do programa
- O histórico de relatórios gerados fica disponível para consulta

---

## Auditoria

### HU13 — Consulta de Logs de Auditoria
**Como** gestor  
**Quero** consultar e exportar logs de auditoria do sistema  
**Para** monitorar alterações em dados sensíveis e garantir a conformidade

**Critérios de Aceitação:**
- Filtros por usuário, tabela, operação, período e ID do objeto
- Exportação em formato CSV
- Apenas gestores têm acesso

---

## Monitoramento

### HU14 — Monitoramento de Saúde do Sistema
**Como** equipe técnica  
**Quero** ter dashboards com métricas de desempenho e alertas sobre problemas  
**Para** identificar e responder rapidamente a incidentes no sistema distribuído

**Critérios de Aceitação:**
- Métricas de banco de dados (conexões, queries lentas)
- Métricas de aplicação (taxa de erros, latência)
- Métricas de infraestrutura (CPU, memória, disco)
- Alertas para conexões altas, disco cheio, fila acumulada
