# Coleta Premiada

Sistema de gestão para programa de incentivo à reciclagem, onde cidadãos ganham pontos por materiais reciclados que podem ser convertidos em benefícios e descontos.

## 📋 Visão Geral

O Coleta Premiada é uma plataforma integrada que gerencia o ciclo completo da reciclagem incentivada:
- **Gestão de Usuários e Roles**: Controle de acesso granular para moradores, supervisores e gestores.
- **Registro de Coletas**: Lógica para registrar pesagens e materiais recolhidos.
- **Cálculo de Pontuação**: Business rules para conversão de materiais em pontos.
- **Auditoria**: Sistema de logs detalhados para todas as ações críticas.

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.12 com Django e Django REST Framework
- **Banco de Dados**: PostgreSQL 16 (Relacional e Auditoria)
- **Mensageria**: RabbitMQ (Fila de processamento assíncrono)
- **Task Queue**: Celery
- **Armazenamento de Objetos**: MinIO (Fotos e evidências)
- **Orquestração**: Docker Compose
- **Auditoria**: Auditoria Customizada (custom_audit)

## 📁 Estrutura do Projeto

```
.
├── core/                    # Monolito Django (Aplicação Principal)
│   ├── accounts/            # Gestão de usuários, perfis e roles
│   ├── collection/          # Registro de coletas e pesagens
│   ├── program/             # Regras de negócio, pontos e benefícios
│   ├── messaging/           # Integração com RabbitMQ
│   └── config/              # Configurações do projeto Django
├── docs/                    # Documentação, ADRs e Diagramas
├── docker-compose.yml       # Orquestração de containers
├── Makefile                 # Atalhos para comandos comuns
└── .env                     # Variáveis de ambiente (não versionado)
```

## 🚀 Como Iniciar o Projeto

### Pré-requisitos

- Docker e Docker Compose instalados.

### Passo a Passo

1. **Clone o repositório**
   ```bash
   git clone https://github.com/rangelro/Coleta-Premiada.git
   cd Coleta-Premiada
   ```

2. **Configure as variáveis de ambiente**
   O projeto utiliza um arquivo `.env` na raiz. Certifique-se de que ele contém as chaves necessárias (baseie-se no `core/config/settings.py` para as variáveis esperadas).

3. **Inicie os containers**
   ```bash
   docker compose up -d
   ```

4. **Verifique se todos os serviços estão rodando**
   ```bash
   docker ps
   ```

### Portas e Acessos

- **API Core**: http://localhost:8001 (Mapeada da porta 8001 interna)
- **Banco de Dados (PostgreSQL)**: localhost:5433 (Exposta para ferramentas externas)
- **Painel do RabbitMQ**: http://localhost:15672
- **Painel do MinIO**: http://localhost:9001

## Monitoramento (Prometheus + Grafana)

A stack de monitoramento é opcional e roda em um compose separado. Requer que a stack principal (`make up`) já esteja no ar, pois o `postgres_exporter` acessa o PostgreSQL via rede `coleta-shared`.

### Como subir

```bash
make monitoring-up
```

### Serviços e portas

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Grafana | http://localhost:3000 | Dashboards de visualização |
| Prometheus | http://localhost:9090 | Coleta e consulta de métricas |
| postgres_exporter | http://localhost:9187/metrics | Métricas do PostgreSQL |
| node_exporter | http://localhost:9100/metrics | Métricas do host (Docker VM) |

### Credenciais padrão

| Serviço | Usuário | Senha |
|---------|---------|-------|
| Grafana | `admin` | `senha_admin_grafana` |

### Configurar datasource Prometheus no Grafana

1. Acesse http://localhost:3000 e faça login
2. Vá em **Connections → Data sources → Add data source**
3. Selecione **Prometheus**
4. Em **URL**, informe `http://prometheus:9090`
5. Clique em **Save & test**

### Outros comandos

```bash
make monitoring-logs   # Ver logs da stack de monitoramento
make monitoring-down   # Derrubar a stack de monitoramento
```

## 💾 Backup e Restore do Banco de Dados

O serviço `db-backup` (ver `./db-backup`) executa `pg_dump` diariamente via cron e mantém uma política de retenção do tipo "diário + semanal":

- **Backups diários**: um por dia, mantidos os `BACKUP_KEEP_DAILY` (padrão 7) mais recentes em `/backups/postgres/daily` (volume `postgres_backups`).
- **Backups semanais**: no dia da semana definido por `BACKUP_WEEKLY_DAY` (padrão 7 = domingo), o backup do dia também é copiado para `/backups/postgres/weekly`, mantendo os `BACKUP_KEEP_WEEKLY` (padrão 4) mais recentes.
- **Agendamento**: configurável via `BACKUP_CRON_SCHEDULE` (padrão `0 2 * * *`, todo dia às 2h).

### Gerar um backup manualmente

```bash
docker compose exec db-backup /scripts/backup.sh
```

### Restaurar um backup

```bash
# Lista os backups disponíveis no volume
docker compose exec db-backup /scripts/restore.sh

# Restaura um arquivo específico (pede confirmação antes de sobrescrever o banco)
docker compose exec db-backup /scripts/restore.sh /backups/postgres/daily/coleta_premiada_2026-06-18_02-00-00.dump
```

`pg_restore --clean --if-exists` é usado internamente, ou seja, a restauração **substitui os dados atuais** do banco de destino.

### Variáveis de ambiente

Ver `BACKUP_CRON_SCHEDULE`, `BACKUP_KEEP_DAILY`, `BACKUP_KEEP_WEEKLY` e `BACKUP_WEEKLY_DAY` no `.env.example`.

### ⚠️ Migrando do serviço antigo (`backup-core`)

O serviço `db-backup` substitui o antigo `backup-core` e reaproveita o mesmo volume nomeado (`backup-data`), mas muda:

- **Ponto de montagem**: de `/backups` para `/backups/postgres`.
- **Formato**: de `.sql.gz` (dump texto + gzip) para `.dump` (formato custom do `pg_dump`, restaurado com `pg_restore`).

Se este volume já tinha backups gerados pelo `backup-core` em produção, esses arquivos `core_*.sql.gz` continuam existindo no volume e passam a aparecer soltos em `/backups/postgres/` (fora de `daily/`/`weekly/`). Eles **não** são enxergados pelo `restore.sh` (que só lista `*.dump`) nem pela política de retenção nova. Antes de subir esta versão em um ambiente com backups antigos:

```bash
# Inspeciona o que existe no volume antes de migrar
docker run --rm -v backup-data:/data alpine ls -la /data

# Remove os backups antigos (.sql.gz) depois de confirmar que não são mais necessários
docker run --rm -v backup-data:/data alpine sh -c "rm -f /data/core_*.sql.gz"
```

## 📖 Documentação Adicional

- [Diagramas de Arquitetura](./docs/diagrams/)
- [ADRs](./docs/adr/)

## ⚙️ Variáveis de Ambiente Principais

```env
POSTGRES_DB=coleta_premiada
POSTGRES_USER=coleta_user
POSTGRES_PASSWORD=coleta_senha_local
POSTGRES_PORT=5432 # Interna do container

RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest

DJANGO_SECRET_KEY=chave-secreta-de-desenvolvimento
DEBUG=True
```

## 🐧 Comandos de Desenvolvimento

Use o `Makefile` ou os comandos Docker diretamente:

```bash
# Executar migrações
docker compose exec core python manage.py migrate

# Criar superusuário
docker compose exec core python manage.py createsuperuser

# Ver logs do sistema
docker compose logs -f core
```
