# Comunicação entre Serviços

## Protocolos Utilizados

| Protocolo | Uso | Direção |
|---|---|---|
| **HTTP/REST** | Frontend → Core API | Síncrono |
| **HTTP/REST** | Frontend → Collection MS | Síncrono |
| **HTTP/REST** | Collection MS → Core API (proxy de perfil) | Síncrono |
| **AMQP 0-9-1** | Core → RabbitMQ → Collection MS (fila `imoveis`) | Assíncrono (event-driven) |
| **AMQP 0-9-1** | Collection MS → RabbitMQ → Core (fila `coletas`) | Assíncrono (event-driven) |
| **HTTP** | App Mobile → Collection MS | Síncrono (com fallback offline) |

---

## Representação Visual do Fluxo de Dados

Para uma visualização melhor do fluxo de dados, acesse:

- [Arquitetura Geral](diagramas/arquitetura_geral.puml)
- [Comunicação entre Serviços](diagramas/comunicacao_servicos.puml)

Abra os arquivos `.puml` no preview do PlantUML para visualizar os diagramas.

### 1. Sincronização de Imóveis (Core → MS)

```
[Core] Imovel.save()
  │
  ├─▶ Signal: publicar_imovel()
  │     └─▶ messaging/producer.publish_message('imoveis', payload)
  │           └─▶ RabbitMQ (durable queue: 'imoveis')
  │                 └─▶ [MS] consumir_imoveis management command
  │                       └─▶ ImovelManager.upsert_from_evento(payload)
  │
  └─▶ Celery: geocodificar_imovel.delay(imovel_id)
        └─▶ GeoPy/Nominatim (geocoding assíncrono)
```

**Payload da fila `imoveis`:**
```json
{
  "inscricao_imobiliaria": "12345",
  "nome": "João",
  "cpf": "000.000.000-00",
  "endereco": "Rua A, 123",
  "acao": "adesao_programa",
  "latitude": null,
  "longitude": null,
  "elegivel": true,
  "ativo": true,
  "proprietario_id": 42,
  "num_moradores": 3,
  "iptu": "123456-7",
  "numero": "123",
  "complemento": "",
  "bairro": "Centro",
  "telefone": "85999999999"
}
```

---

### 2. Sincronização de Coletas (MS → Core)

```
[MS] Coleta criada (POST /api/coletas ou /api/sincronizar)
  │
  ├─▶ Salva no MongoDB (Coleta.objects.create())
  │
  └─▶ services/fila.publicar_coleta(coleta_id, inscricao, peso, data_hora)
        └─▶ RabbitMQ (durable queue: 'coletas')
              └─▶ [Core] consume_queue management command
                    ├─▶ Verifica duplicata (id_microservico)
                    ├─▶ Busca Imovel por inscricao_imobiliaria
                    ├─▶ Busca Programa ativo
                    ├─▶ Calcula pontuação = peso × constante
                    ├─▶ Cria RegistroColeta
                    ├─▶ Atualiza SaldoPontos com teto de 40%
                    └─▶ basic_ack() / basic_nack()
```

**Payload da fila `coletas`:**
```json
{
  "coleta_id": "550e8400-e29b-41d4-a716-446655440000",
  "inscricao_imobiliaria": "12345",
  "peso_total_kg": "12.500",
  "data_hora": "2026-07-10T14:30:00-03:00"
}
```

---

### 3. Proxy de Perfil (MS → Core HTTP)

Endpoints supervisor no MS usam chamada HTTP síncrona ao Core para validar perfil:

```
[MS] GET /api/supervisor/imoveis
  │
  ├─▶ Decodifica JWT do Core manualmente (CORE_JWT_SECRET_KEY)
  ├─▶ HTTP GET {CORE_API_URL}/api/accounts/auth/me (forward JWT)
  │     └─▶ [Core] Retorna { id, email, perfil, cidade, ... }
  ├─▶ Valida perfil in ['supervisor', 'gestor', 'gerente_geral']
  └─▶ Retorna dados escopados por cidade
```

---

### 4. Frontend → Backends (HTTP REST)

```
[Frontend/Next.js]
  │
  ├─▶ CORE_API_URL=http://core:8000
  │     ├─▶ POST /api/token/ (login)
  │     ├─▶ POST /api/token/refresh/
  │     ├─▶ GET/POST/PATCH/DELETE /api/accounts/*
  │     ├─▶ GET/POST/PATCH/DELETE /api/program/*
  │     ├─▶ GET/POST /api/collection/*
  │     ├─▶ GET /api/audit/*
  │     └─▶ POST /api/reports/*
  │
  └─▶ COLLECTION_API_URL=http://coleta-ms-app:8001
        ├─▶ GET /api/imoveis/buscar
        ├─▶ GET /api/imoveis/proximos
        ├─▶ GET /api/coletas/morador
        └─▶ GET /api/supervisor/*
```

---

### 5. App Mobile → Collection MS

```
[App/React Native]
  │
  └─▶ API_BASE_URL=http://192.168.0.14:8002/api/
        ├─▶ POST /api/auth/login (login do coletor)
        ├─▶ GET /api/imoveis/proximos (geolocalização)
        ├─▶ GET /api/imoveis/buscar (por endereço)
        ├─▶ POST /api/coletas (criação com upload de foto)
        ├─▶ POST /api/sincronizar (batch sync offline)
        └─▶ GET /api/coletas/historico
```

**Fluxo offline:**
```
[Mobile] POST /api/coletas
  ├─▶ Tenta enviar para API
  ├─▶ Se falha de rede:
  │     └─▶ Interceptor Axios salva no SQLite local
  │           └─▶ ColetaRepository.save() com offline_id
  │
  └─▶ Background: useAutoSync()
        └─▶ ColetaRepository.getAllPendentes()
              └─▶ POST /api/sincronizar (envio batch)
```

---

## Estratégias de Autenticação e Autorização

### Core API (Django + SimpleJWT)

| Aspecto | Configuração |
|---|---|
| **Algoritmo** | HS256 |
| **Access Token** | 8 horas |
| **Refresh Token** | 7 dias, rotação ativada, blacklist |
| **Transporte** | Header `Authorization: Bearer <token>` |
| **Perfis (RBAC)** | `morador` < `supervisor` < `gestor` < `gerente_geral` |
| **Permissões** | Classes DRF: IsMorador, IsGestor, IsSupervisor, IsGerenteGeral, IsOwnerOrGestor, ReadOnlyOrGestor |
| **Escopo** | Gestor/supervisor restritos à sua cidade (`scoping.py`) |

### Collection MS (Dual Auth)

| Cenário | Estratégia |
|---|---|
| **Agente de coleta (mobile)** | JWT próprio (SimpleJWT) emitido pelo MS para coletores |
| **Morador/Supervisor (web)** | JWT do Core validado manualmente via `CORE_JWT_SECRET_KEY` + proxy HTTP ao Core para perfil |
| **Acesso público** | `AllowAny` + validação manual do JWT do Core |

### Frontend (httpOnly Cookies)

| Aspecto | Configuração |
|---|---|
| **Armazenamento** | httpOnly cookies (`accessToken`, `refreshToken`) |
| **Renovação** | Middleware `proxy.ts` tenta refresh automático se access expirou |
| **Google OAuth** | Fluxo code → token → JWT (sem state manager) |

### App Mobile (SecureStore)

| Aspecto | Configuração |
|---|---|
| **Armazenamento** | expo-secure-store (chave-valor criptografada) |
| **Interceptor** | Headers Authorization injetados automaticamente via Axios interceptor |
| **Sessão** | Restaurada ao abrir o app; 401 limpa SecureStore |

---

## Tratamento de Falhas na Comunicação

### Mensageria (RabbitMQ)

| Situação | Comportamento |
|---|---|
| **Payload inválido** | `basic_nack(requeue=False)` — descarta para dead letter |
| **Erro de processamento** | `basic_nack(requeue=True)` — tenta novamente |
| **Conexão perdida (consumer)** | Loop infinito com `time.sleep(5)` + reconnect |
| **Falha ao publicar (producer)** | Erro logado, operação não abortada (coleta salva localmente com `sincronizado_core=False`) |

### HTTP

| Situação | Comportamento |
|---|---|
| **401 do Core (MS proxy)** | Retorna 403 ao frontend |
| **Core offline (MS proxy)** | Timeout de 5s, retorna erro |
| **Rede offline (mobile)** | Salva em SQLite, sync posterior |
| **API indisponível (frontend)** | Server Action retorna estado de erro para `useActionState` |
