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
- **Grafana**: http://localhost:3000

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
