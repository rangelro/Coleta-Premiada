# Documentação de Endpoints – Coleta Premiada

Este documento detalha todos os endpoints HTTP expostos e consumidos pelo ecossistema **Coleta Premiada**, cobrindo o **Core API (Django + DRF)** e o **MS de Coleta (Django + MongoDB)**.

---

## ─── CORE API (Porta 8001) ───

Base URL: `http://localhost:8001/api`  
Autenticação: Bearer JWT (`Authorization: Bearer <token>`)

---

### 1. Autenticação & Conta

#### POST `/token/`
**Descrição:** Autentica o usuário na plataforma e gera os tokens JWT de acesso e renovação.
*   **Autenticação:** Nenhuma.
*   **Body (Request):**
    ```json
    {
      "email": "morador@coleta.com",
      "password": "senha"
    }
    ```
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "access": "eyJhbGciOi...",
          "refresh": "eyJhbGciOi..."
        }
        ```
    *   `401 Unauthorized`: E-mail ou senha incorretos.

#### POST `/token/refresh/`
**Descrição:** Renova o token de acesso expirado utilizando o token de atualização.
*   **Autenticação:** Nenhuma.
*   **Body (Request):**
    ```json
    {
      "refresh": "refresh_token_string"
    }
    ```
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "access": "new_access_token_string",
          "refresh": "new_refresh_token_string"
        }
        ```

#### GET `/accounts/auth/me`
**Descrição:** Obtém os dados cadastrais do usuário atualmente autenticado.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "id": 2,
          "email": "morador@coleta.com",
          "cpf": "123.456.789-01",
          "nome": "João Silva",
          "perfil": "morador",
          "ativo": true,
          "roles": []
        }
        ```

#### PATCH `/accounts/auth/me`
**Descrição:** Atualiza os dados de perfil (nome e CPF) do próprio usuário logado.
*   **Autenticação:** Bearer JWT.
*   **Body (Request - Parcial):**
    ```json
    {
      "nome": "João Silva Alterado",
      "cpf": "98765432109"
    }
    ```
*   **Respostas:**
    *   `200 OK`: Dados de usuário atualizados.

---

### 2. Portal do Cidadão (`/accounts/me/`)
Acesso restrito ao perfil `morador`.

#### GET `/accounts/me/points`
**Descrição:** Retorna o saldo acumulado total de pontos obtido por coletas.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "pontos_acumulados": 185
        }
        ```

#### GET `/accounts/me/benefits`
**Descrição:** Retorna os descontos de IPTU consolidados por ciclo (ano/mês) do morador.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        [
          {
            "id": 1,
            "imovel": 2,
            "programa": 1,
            "ciclo": "06-2025",
            "desconto_percentual": 5.0,
            "atualizado": "2025-06-27T00:15:00Z"
          }
        ]
        ```

#### GET `/accounts/me/program`
**Descrição:** Busca o programa de incentivo de reciclagem atualmente active.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "id": 1,
          "nome": "Programa de Incentivo à Reciclagem 2025",
          "descricao": "Ganhe desconto no seu IPTU reciclando",
          "data_inicio": "2025-01-01",
          "data_fim": "2025-12-31",
          "ativo": true,
          "desconto_maximo": 40.0,
          "regras": {
            "pontos_por_real": 200.0,
            "minimo_para_beneficio": 100,
            "permite_acumulo_ciclos": true
          }
        }
        ```
    *   `404 Not Found`: Nenhum programa ativo cadastrado.
        ```json
        {
          "detail": "Nenhum programa ativo."
        }
        ```

---

### 3. Imóveis (`/program/properties`)

#### GET `/program/properties`
**Descrição:** Lista unidades imobiliárias participantes. Se autenticado como morador, retorna apenas as dele.
*   **Autenticação:** Bearer JWT.
*   **Query Params:**
    *   `bairro` (string - opcional): Filtra pelo nome do bairro.
    *   `cidade` (string - opcional): Filtra por cidade.
    *   `ativo` (boolean - opcional): Filtra imóveis ativos ou inativos.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "id": 2,
              "inscricao": "01.02.003.0045.001",
              "titular": 2,
              "cep": "62010-000",
              "logradouro": "Rua das Flores",
              "numero": "123",
              "complemento": "Apto 101",
              "bairro": "Centro",
              "cidade": "Sobral",
              "estado": "CE",
              "num_moradores": 3,
              "ativo": true,
              "data_adesao": "2025-06-27",
              "moradores": [
                {
                  "id": 2,
                  "email": "morador@coleta.com",
                  "nome": "João Silva",
                  "cpf": "123.***.***-01"
                }
              ]
            }
          ]
        }
        ```

#### POST `/program/properties`
**Descrição:** Cadastra um novo imóvel residencial vinculado ao titular.
*   **Autenticação:** Bearer JWT.
*   **Body (Request):**
    ```json
    {
      "inscricao": "01.02.003.0045.001",
      "titular": 2,
      "cep": "62010-000",
      "logradouro": "Rua das Flores",
      "numero": "123",
      "complemento": "Apto 101",
      "bairro": "Centro",
      "cidade": "Sobral",
      "estado": "CE",
      "num_moradores": 3
    }
    ```
*   **Respostas:**
    *   `201 Created`: Imóvel salvo e publicado no RabbitMQ.

---

### 4. Histórico de Coletas & Evidências (`/collection/collections`)

#### GET `/collection/collections`
**Descrição:** Lista coletas efetuadas. Se autenticado como morador, retorna apenas as dele.
*   **Autenticação:** Bearer JWT.
*   **Query Params:**
    *   `page` (int - opcional): Página de paginação (default: 1).
    *   `data_inicio` (string - opcional): Filtra coletas a partir do dia (formato YYYY-MM-DD).
    *   `data_fim` (string - opcional): Filtra coletas até o dia (formato YYYY-MM-DD).
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "count": 5,
          "results": [
            {
              "id": 1,
              "id_microservico": "mc-uuid-2025-06-01",
              "imovel": 2,
              "pontuacao": 25,
              "data_hora_coleta": "2025-06-15T10:30:00Z",
              "peso_kg": "12.50"
            }
          ]
        }
        ```

#### GET `/collection/collections/{id}/evidences`
**Descrição:** Retorna a galeria de fotos/evidências vinculadas a uma pesagem.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        [
          {
            "id": 5,
            "coleta": 1,
            "descricao": "Pesagem de papelão e pet",
            "arquivo_url": "http://minio:9000/bucket-coletas/ev.jpg",
            "enviada_em": "2025-06-15T10:32:00Z",
            "enviada_por": 2
          }
        ]
        ```

---

### 5. Contestações (`/collection/disputes`)

#### GET `/collection/disputes`
**Descrição:** Lista as contestações abertas por moradores. Moradores enxergam apenas as próprias.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "count": 1,
          "results": [
            {
              "id": 1,
              "coleta": 1,
              "aberta_por": 2,
              "motivo": "Peso divergente do registrado na balança.",
              "status": "em_analise",
              "analisada_por": null,
              "resposta": null,
              "aberta_em": "2025-06-27T01:00:00Z",
              "atualizada_em": "2025-06-27T01:00:00Z"
            }
          ]
        }
        ```

#### POST `/collection/disputes`
**Descrição:** Abre um ticket de contestação sobre uma coleta. Restrito ao perfil `morador`.
*   **Autenticação:** Bearer JWT.
*   **Body (Request):**
    ```json
    {
      "coleta": 1,
      "motivo": "O peso registrado está menor do que o real pesado na balança."
    }
    ```
*   **Respostas:**
    *   `201 Created`: Contestação aberta.

---
---

## ─── MICROSERVIÇO DE COLETA (Porta 8002) ───

Base URL: `http://localhost:8002/api`  
Autenticação: Bearer JWT (`Authorization: Bearer <token_coletor>`) próprio do coletor de campo.

---

### 1. Autenticação do Coletor

#### POST `/auth/register`
**Descrição:** Registra um novo coletor (agente de campo) no MongoDB.
*   **Autenticação:** Nenhuma.
*   **Body (Request):**
    ```json
    {
      "matricula": "C-12345",
      "senha": "senha_coletor",
      "nome": "Carlos Agente",
      "email": "carlos@coleta.com",
      "zona": "Norte",
      "cargo": "coletor"
    }
    ```

#### POST `/auth/login`
**Descrição:** Autentica o coletor na operação de campo.
*   **Autenticação:** Nenhuma.
*   **Body (Request):**
    ```json
    {
      "matricula": "C-12345",
      "senha": "senha_coletor"
    }
    ```
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "token": "eyJhbGciOi...",
          "user": {
            "id": "60c72b2f9b1d8a0015...",
            "nome": "Carlos Agente",
            "matricula": "C-12345",
            "email": "carlos@coleta.com",
            "zona": "Norte",
            "role": "coletor"
          }
        }
        ```

---

### 2. Operações de Campo

#### GET `/imoveis/buscar`
**Descrição:** Busca um imóvel cadastrado no microserviço por QRCode, número da inscrição ou logradouro.
*   **Autenticação:** Bearer JWT (Coletor).
*   **Query Params:**
    *   `tipo` (string): `qrcode` \| `numero` \| `endereco`.
    *   `valor` (string): O termo de busca.
*   **Respostas:**
    *   `200 OK`: Dados cadastrais do imóvel.

#### POST `/coletas`
**Descrição:** Registra uma pesagem realizada em campo no imóvel.
*   **Autenticação:** Bearer JWT (Coletor).
*   **Body (Request - Multipart Form Data):**
    *   `imovel_id` (string): ObjectId do imóvel no MongoDB.
    *   `peso_total_kg` (decimal): Peso em kg.
    *   `data_hora` (ISO Datetime): Data e hora da coleta.
    *   `foto` (File): Foto/evidência da pesagem.
*   **Respostas:**
    *   `201 Created`: Registro salvo localmente e encaminhado para fila RabbitMQ.

#### POST `/sincronizar`
**Descrição:** Envia lotes (batch) de coletas salvas em modo offline para o banco MongoDB.
*   **Autenticação:** Bearer JWT (Coletor).
*   **Body (Request):**
    ```json
    {
      "coletas": [
        {
          "imovel_id": "60c72b2f9b1d...",
          "peso_total_kg": "14.2",
          "data_hora": "2025-06-27T10:00:00Z",
          "offline_id": "uuid-temp-1"
        }
      ]
    }
    ```
*   **Respostas:**
    *   `200 OK` ou `207 Multi-Status` (em caso de sincronização parcial).
