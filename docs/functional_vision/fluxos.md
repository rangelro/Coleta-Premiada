# Fluxos Principais do Sistema — Coleta Premiada

---

## Fluxo 1: Ciclo de Vida do Programa de Reciclagem

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌─────────────┐
│ Gerente  │    │ Gestor   │    │ Morador  │    │   Coletor    │    │   Gestor    │
│ Geral    │    │          │    │          │    │  (Mobile)    │    │             │
│          │    │          │    │          │    │              │    │             │
│ Cria     │───→│ Cria     │───→│ Cadastra │───→│  Coleta      │───→│ Executa     │
│ Cidade   │    │ Programa │    │ Imóvel   │    │  Resíduos    │    │ Consolidação│
│          │    │ + Ciclo  │    │          │    │              │    │             │
└──────────┘    └──────────┘    └──────────┘    └──────────────┘    └──────┬──────┘
                                                                           │
                                                                           ▼
                                                                   ┌──────────────┐
                                                                   │   Morador    │
                                                                   │  recebe      │
                                                                   │  desconto    │
                                                                   │  IPTU        │
                                                                   └──────────────┘
```

**Passos:**
1. Gerente Geral cadastra o município no sistema
2. Gestor cria o programa de reciclagem com regras (pontos por real, mínimo para benefício)
3. Gestor cria ciclos dentro do programa (ex: mensal)
4. Morador cadastra seu imóvel para aderir ao programa
5. Coletor realiza coletas no imóvel utilizando o aplicativo mobile
6. Gestor executa a consolidação ao final do ciclo
7. Morador tem o desconto de IPTU calculado e aplicado

---

## Fluxo 2: Autenticação e Acesso

### 2.1 Morador, Supervisor ou Gestor (Web)

```
                    ┌──────────┐
                    │  Usuário  │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  Login   │
                    │ Web      │
                    └────┬─────┘
                    ┌────┴─────┐
                    │ JWT      │
                    │ (8h)     │
                    └────┬─────┘
                         │
                         ▼
              ┌──────────────────┐
              │ Redireciona para │
              │ dashboard do     │
              │ perfil           │
              │ (morador/gestor/ │
              │  supervisor)     │
              └──────────────────┘
```

**Opções de login:**
- E-mail e senha
- Google OAuth (apenas morador)

### 2.2 Coletor (Mobile)

```
                    ┌──────────┐
                    │  Coletor  │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  Login   │
                    │ Mobile   │
                    │ matrícula│
                    │ + senha  │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ Token    │
                    │ armazen. │
                    │ secure   │
                    │ store    │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ Dashboard│
                    │ do dia   │
                    └──────────┘
```

---

## Fluxo 3: Coleta em Campo (Mobile)

```
┌──────────────────────────────────────────────────────────────────┐
│                        COLETOR NO CAMPO                          │
└──────────────────────────────────────────────────────────────────┘

  1. IDENTIFICAR IMÓVEL
     ├── Por número IPTU (digitação)
     ├── Por QR Code (leitura da câmera)
     └── Por endereço (busca textual)
         │
         ▼ Dados do imóvel: endereço, morador, elegibilidade
         │
  2. PESAR MATERIAL
     ├── Inserir peso em kg (teclado numérico personalizado)
     └── Apenas peso total (sem separação por tipo de material)
         │
  3. FOTOGRAFAR (OPCIONAL)
     ├── Capturar foto da coleta
     └── Adicionar observações (opcional)
         │
  4. CONFIRMAR E SALVAR
     ├── Revisar dados: imóvel, peso, foto
     ├── Salvar localmente (SQLite) → offline-first
     └── Sincronizar com servidor (se online)
         │
         ▼
  ┌────────────────┐
  │   SUCESSO      │
  │ Código da      │
  │ coleta gerado  │
  └────────────────┘
```

---

## Fluxo 4: Sincronização de Dados

```
   COLETOR (Mobile)                    MICROSSERVIÇO                    CORE (Backend)
         │                                  │                              │
         │   POST /api/coletas              │                              │
    [online] ──────────────────────────────→│                              │
         │                            ┌─────┴─────┐                        │
         │                            │ Salva em  │                        │
         │                            │ MongoDB   │                        │
         │                            └─────┬─────┘                        │
         │                                  │                              │
         │                                  │  Publica na fila "coletas"   │
         │                                  │─────────────────────────────→│
         │                                  │         (RabbitMQ)           │
         │                                  │                              │
         │                                  │                     ┌────────┴────────┐
         │                                  │                     │ Processa coleta │
         │                                  │                     │ Calcula pontos  │
         │                                  │                     │ SaldoPontos     │
         │                                  │                     └─────────────────┘
         │                                  │                              │
         │   offline-first:                 │                              │
         │   Salva em SQLite local          │                              │
         │   Depois sincroniza:             │                              │
         │   POST /api/sincronizar (lote)   │                              │
         │───────────────────────────────→  │                              │
```

---

## Fluxo 5: Propriedade → Sincronização Cross-Service

```
   CORE (Backend)                    RABBITMQ                    MICROSSERVIÇO
         │                              │                              │
         │  Imóvel criado/atualizado     │                              │
         │  no Core (PostgreSQL)         │                              │
         └──────────────────────────────→│                              │
                    imoveis queue        │                              │
                                         │  consumir_imoveis            │
                                         │─────────────────────────────→│
                                         │                              │
                                         │                       ┌──────┴──────┐
                                         │                       │ Upsert      │
                                         │                       │ Imóvel no   │
                                         │                       │ MongoDB     │
                                         │                       └─────────────┘
```

---

## Fluxo 6: Consolidação de Desconto IPTU

```
   GESTOR (Web)                        CORE (Backend)
         │                              │
         │  POST /consolidations/run    │
         │  (programa + ciclo)          │
         │─────────────────────────────→│
         │                              │
         │                       ┌──────┴──────┐
         │                       │ Busca coletas│
         │                       │ do ciclo     │
         │                       │ (não consol.)│
         │                       └──────┬──────┘
         │                              │
         │                       ┌──────▼──────┐
         │                       │ Calcula      │
         │                       │ pontuação    │
         │                       │ por imóvel   │
         │                       └──────┬──────┘
         │                              │
         │                       ┌──────▼──────┐
         │                       │ Aplica regras│
         │                       │ - mínimo p/ │
         │                       │   benefício  │
         │                       │ - teto 40%  │
         │                       │ - acumulação │
         │                       └──────┬──────┘
         │                              │
         │                       ┌──────▼──────┐
         │                       │ Gera        │
         │                       │ Benefício   │
         │                       │ (desconto   │
         │                       │  IPTU)      │
         │                       └──────┬──────┘
         │                              │
         │  Status: concluída           │
         │  Ciclo fechado              │
         │◄─────────────────────────────│
```

---

## Fluxo 7: Contestação de Coleta

```
   MORADOR (Web)                   CORE (Backend)                  GESTOR (Web)
         │                              │                              │
         │  Visualiza coleta            │                              │
         │  no histórico                │                              │
         │                              │                              │
         │  POST /disputes              │                              │
         │  (motivo > 10 caracteres)    │                              │
         │─────────────────────────────→│                              │
         │                              │                              │
         │                       ┌──────┴──────┐                       │
         │                       │ Status:     │                       │
         │                       │ "aberta"    │                       │
         │                       └─────────────┘                       │
         │                              │                              │
         │                              │  Lista contestações          │
         │                              │  pendentes (dashboard)       │
         │                              │─────────────────────────────→│
         │                              │                              │
         │                              │  Responde:                   │
         │                              │  aceita / negada / análise  │
         │                              │◄─────────────────────────────│
         │                              │                              │
         │  Status atualizado           │                              │
         │◄─────────────────────────────│                              │
```

---

## Fluxo 8: Geração de Relatório com IA

```
   GESTOR (Web)                   CORE (Backend)                  SERVIÇO LLM
         │                              │                              │
         │  POST /reports/generate      │                              │
         │  (tipo, programa)            │                              │
         │─────────────────────────────→│                              │
         │                              │                              │
         │                       ┌──────┴──────┐                       │
         │                       │ Consulta     │                       │
         │                       │ dados do     │                       │
         │                       │ programa     │                       │
         │                       └──────┬──────┘                       │
         │                              │                              │
         │                              │  Envia prompt com dados     │
         │                              │─────────────────────────────→│
         │                              │                              │
         │                              │  Resposta narrativa         │
         │                              │◄─────────────────────────────│
         │                              │                              │
         │                       ┌──────┴──────┐                       │
         │                       │ Salva        │                      │
         │                       │ RelatorioLLM │                      │
         │                       └─────────────┘                       │
         │                              │                              │
         │  Relatório gerado            │                              │
         │◄─────────────────────────────│                              │
```

---

## Fluxo 9: Monitoramento (Observabilidade)

```
                    ┌──────────────────────┐
                    │    Prometheus         │
                    │  scrape_interval: 15s │
                    │  retention: 30d       │
                    └────┬────────┬────────┘
                    ┌────┘        └────┐
              ┌─────▼─────┐      ┌─────▼─────┐
              │ django-core │      │ django-ms │
              │ /metrics    │      │ /metrics  │
              └─────┬─────┘      └─────┬─────┘
              ┌─────▼─────┐      ┌─────▼─────┐
              │postgres-   │      │mongodb-    │
              │exporter    │      │exporter    │
              └─────┬─────┘      └─────┬─────┘
              ┌─────▼─────┐      ┌─────▼─────┐
              │ node-      │      │ cadvisor   │
              │ exporter   │      │ (container)│
              └─────┬─────┘      └─────┬─────┘
                    └────┬────────┬────┘
                         │        │
                    ┌────▼────┐ ┌─▼──────────┐
                    │ Grafana │ │ Alertas     │
                    │ Dashbrd │ │ (Prometheus)│
                    │ 3 pain. │ │ 4 regras    │
                    └─────────┘ └─────────────┘
```
