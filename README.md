# Coleta Premiada

Sistema de gestão para programa de incentivo à reciclagem, onde cidadãos ganham pontos por materiais reciclados que podem ser convertidos em descontos no IPTU.

## 📋 Visão Geral

O Coleta Premiada é uma aplicação distribuída composta por:
- **Microserviço de Coleta**: Responsável por receber e registrar as pesagens de materiais reciclados
- **Serviço Core (Monolito)**: Gerencia os cadastros de imóveis, cálculo de descontos e saldos de pontos
- **Infraestrutura**: Bancos de dados, fila de mensagens e armazenamento de objetos

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.12 com Django
- **Bancos de Dados**:
  - PostgreSQL (Core - dados relacionais)
  - MongoDB (Collection Microservice - documentos)
- **Mensageria**: RabbitMQ
- **Armazenamento de Objetos**: MinIO (compatível com S3)
- **Orquestração**: Docker Compose
- **API**: RESTful com Django REST Framework

## 📁 Estrutura do Projeto

```
.
├── apps/                    # Aplicações frontend (vazio atualmente)
├── services/                # Serviços backend
│   ├── collection-microservice/  # Microserviço de coleta (Django)
│   └── core/                  # Serviço core (Django monolito)
├── infra/                   # Configurações de infraestrutura
├── docs/                    # Documentação e diagramas
├── docker-compose.yml       # Orquestração dos containers
├── .env.example             # Exemplo de variáveis de ambiente
└── demo_comunicacao.sh      # Script de demonstração do fluxo
```

## 🚀 Como Iniciar o Projeto

### Pré-requisitos

- Docker e Docker Compose instalados
- Porta 8000, 8001, 5432, 27017, 5672, 9000, 9001 disponíveis

### Passo a Passo

1. **Clone o repositório**
   ```bash
   git clone <repository-url>
   cd Coleta Premiada
   ```

2. **Configure as variáveis de ambiente**
   ```bash
   cp .env.example .env
   # Edite o .env conforme necessário (especialmente a SECRET_KEY do Django)
   ```

3. **Inicie os containers**
   ```bash
   docker compose up -d
   ```

4. **Aguarde a inicialização** (aproximadamente 30 segundos para todos os serviços ficarem prontos)

5. **Verifique se todos os serviços estão rodando**
   ```bash
   docker compose ps
   ```

### Serviços Disponíveis

- **API do Microserviço de Coleta**: http://localhost:8001
- **API do Serviço Core**: http://localhost:8000
- **Painel do RabbitMQ**: http://localhost:15672 (usuário: rabbit_user, senha: rabbit_senha_local)
- **Painel do MinIO**: http://localhost:9001 (usuário: minio_admin, senha: minio_senha_local)
- **Admin do Django**: http://localhost:8000/admin/

## 📖 Documentação

- [Diagramas de Arquitetura](./docs/diagrams/)
- [ADR (Architecture Decision Records)](./docs/adr/)
- [Documentação do Processo de Software](./docs/adr/Processo%20de%20Software%20-%20Coleta%20Premiada.pdf)

## 🔄 Fluxo de Funcionamento

1. O coletor envia os dados da pesagem via POST para o Microserviço de Coleta
2. O Microserviço persiste os dados no MongoDB e publica uma mensagem no RabbitMQ
3. O Core Consumer lê a mensagem do RabbitMQ, calcula o desconto e salva no PostgreSQL
4. O saldo de pontos é atualizado e pode ser consultado através da API do Core

## 🧪 Demonstração

Um script de demonstração está disponível para mostrar o fluxo completo:

```bash
bash demo_comunicacao.sh
```

Este script irá:
1. Verificar se todos os containers estão rodando
2. Simular 3 coletas de diferentes materiais
3. Mostrar a persistência no MongoDB
4. Aguardar o processamento pelo Core Consumer
5. Exibir os resultados no PostgreSQL
6. Mostrar as regras de negócio aplicadas

## ⚙️ Variáveis de Ambiente

Copie o `.env.example` para `.env` e ajuste conforme necessário:

```env
# PostgreSQL (banco do Monolito Core)
POSTGRES_DB=coleta_premiada
POSTGRES_USER=coleta_user
POSTGRES_PASSWORD=coleta_senha_local

# MongoDB (banco do Microserviço de Coleta)
MONGO_INITDB_DATABASE=coleta_db
MONGO_USER=mongo_user
MONGO_PASSWORD=mongo_senha_local

# RabbitMQ (fila de mensagens)
RABBITMQ_DEFAULT_USER=rabbit_user
RABBITMQ_DEFAULT_PASS=rabbit_senha_local

# MinIO (armazenamento de fotos)
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=minio_senha_local

# Django
DJANGO_SECRET_KEY=coloque_aqui_uma_chave_secreta_forte
DEBUG=True
```

## 🐧 Desenvolvimento

Para desenvolver em um dos serviços:

```bash
# Acessar o container do microserviço de coleta
docker compose exec collection-microservice bash

# Acessar o container do core
docker compose exec core bash

# Executar migrações (se necessário)
docker compose exec core python manage.py makemigrations
docker compose exec core python manage.py migrate

# Criar superuser do Django
docker compose exec core python manage.py createsuperuser
```
