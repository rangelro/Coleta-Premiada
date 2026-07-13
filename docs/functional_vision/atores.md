# Atores do Sistema — Coleta Premiada

## 1. Morador (Cidadão/Residente)

| Atributo | Descrição |
|----------|-----------|
| **Descrição** | Morador/responsável por um imóvel participante do programa de reciclagem |
| **Objetivo** | Reciclar resíduos e acumular pontos para obter desconto no IPTU |
| **Canais** | Web (Frontend Next.js) |
| **Autenticação** | E-mail/senha ou Google OAuth |

**Capacidades:**
- Cadastrar-se no sistema (autocadastro como morador)
- Cadastrar seu imóvel para participar do programa
- Visualizar histórico de coletas do seu imóvel
- Acompanhar saldo de pontos acumulados
- Visualizar descontos de IPTU gerados por ciclo
- Abrir contestações sobre registros de coleta
- Gerenciar perfil (nome, CPF)

---

## 2. Coletor (Agente de Campo)

| Atributo | Descrição |
|----------|-----------|
| **Descrição** | Agente responsável por realizar a coleta de materiais recicláveis nos imóveis |
| **Objetivo** | Registrar coletas de materiais recicláveis em campo |
| **Canais** | Mobile (App React Native / Expo) |
| **Autenticação** | Matrícula e senha |

**Capacidades:**
- Autenticar-se no aplicativo mobile
- Visualizar dashboard com métricas do dia (kg coletados, número de coletas)
- Localizar imóveis próximos em mapa interativo
- Identificar imóvel por número IPTU, QR Code ou endereço
- Registrar coleta com peso (4 etapas: identificar, pesar, fotografar, confirmar)
- Visualizar histórico de coletas realizadas
- Gerenciar sincronização de dados offline
- Baixar mapas offline para áreas sem conectividade
- Visualizar perfil e status de conectividade

---

## 3. Supervisor

| Atributo | Descrição |
|----------|-----------|
| **Descrição** | Profissional de nível operacional que gerencia as operações no município |
| **Objetivo** | Supervisionar imóveis, coletas e constantes de pontuação |
| **Canais** | Web (Frontend Next.js) |
| **Autenticação** | E-mail/senha (criado por Gestor) |
| **Escopo** | Vinculado a uma única Cidade |

**Capacidades:**
- Visualizar todos os imóveis do município
- Gerenciar cadastro de imóveis (criar, editar)
- Visualizar histórico geral de coletas
- Atualizar constante de pontuação (pontos por kg)
- Acessar relatórios operacionais

---

## 4. Gestor (Gerente Municipal)

| Atributo | Descrição |
|----------|-----------|
| **Descrição** | Administrador municipal responsável pela gestão do programa |
| **Objetivo** | Configurar e operar o programa de reciclagem no município |
| **Canais** | Web (Frontend Next.js) |
| **Autenticação** | E-mail/senha (criado por outro Gestor ou Gerente Geral) |
| **Escopo** | Vinculado a uma única Cidade |

**Capacidades:**
- Acessar dashboard executivo com KPIs e rankings
- Gerenciar programas de reciclagem (criar, editar, ativar)
- Configurar regras dos programas (pontos por real, mínimo para benefício)
- Gerenciar ciclos de consolidação (abrir, fechar)
- Executar consolidação de pontos para desconto IPTU
- Gerenciar usuários do município (criar, ativar/desativar)
- Gerenciar papéis e permissões personalizadas
- Visualizar e exportar logs de auditoria
- Analisar contestações de moradores
- Gerar relatórios narrativos via IA
- Gerenciar imóveis

---

## 5. Gerente Geral (Super Administrador)

| Atributo | Descrição |
|----------|-----------|
| **Descrição** | Administrador global do sistema com visão de todas as cidades |
| **Objetivo** | Gerenciar cidades e supervisionar a operação como um todo |
| **Canais** | API (via Gestor) |
| **Autenticação** | E-mail/senha (criado por outro Gerente Geral) |
| **Escopo** | Irrestrito — todas as cidades |

**Capacidades:**
- Gerenciar cidades cadastradas no sistema (criar, editar)
- Visualizar dados de qualquer município
- **Restrições:** Não pode criar/editar programas, executar consolidações ou gerenciar regras de pontuação

---

## 6. Sistemas Externos

| Ator | Descrição | Interação |
|------|-----------|-----------|
| **Google OAuth** | Provedor de identidade externo | Autenticação social de moradores |
| **OpenStreetMap (Nominatim)** | Serviço de geocodificação | Conversão de endereços em coordenadas geográficas |
| **DeepSeek API** | Provedor de IA generativa | Geração de relatórios narrativos em linguagem natural |
| **LM Studio** | LLM local (opcional) | Alternativa ao DeepSeek para geração de relatórios |
| **MinIO** | Armazenamento de objetos S3 | Armazenamento de fotos de evidência de coleta |
