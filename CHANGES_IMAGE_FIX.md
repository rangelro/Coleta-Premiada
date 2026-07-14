# Fix: Imagens de coleta não exibidas no frontend

## Problema

Imagens enviadas pelo app móvel nunca chegavam ao browser. O fluxo quebrava em múltiplos pontos entre o microserviço, o core e o frontend.

## Causa raiz

1. `foto_url` nunca era incluída no payload publicado na fila RabbitMQ
2. O consumer do core não lia `foto_url` e não criava registros `Evidencia`
3. URL pública do MinIO usava o hostname interno do Docker (`minio:9000`), inacessível pelo browser
4. Core não recebia as credenciais do MinIO via docker-compose
5. `RegistroColetaSerializer` não expunha `evidencias`

---

## Arquivos modificados

### `cp-collection-ms`

**`coleta/services/fila.py`**
- Adicionado parâmetro `foto_url: str = ''` em `publicar_coleta()`
- Campo `foto_url` incluído no payload da mensagem RabbitMQ

**`coleta/services/storage.py`**
- URL pública agora usa `MINIO_PUBLIC_ENDPOINT` em vez de `MINIO_ENDPOINT`

**`config/settings.py`**
- Adicionado `MINIO_PUBLIC_ENDPOINT = os.getenv('MINIO_PUBLIC_ENDPOINT', MINIO_ENDPOINT)`

**`coleta/views.py`**
- As duas chamadas a `publicar_coleta()` (registro online e sync offline) passam `foto_url`

**`coleta/management/commands/sincronizar_coletas.py`**
- Sync em lote também passa `foto_url`

**`.env.example`**
- `MINIO_ENDPOINT` corrigido para `minio:9000` (interno)
- Adicionado `MINIO_PUBLIC_ENDPOINT=localhost:9000` (público)

---

### `Coleta-Premiada` (core)

**`core/collection/management/commands/consume_queue.py`**
- Lê `foto_url` do payload da fila
- Cria `Evidencia` automaticamente ao processar cada coleta com foto

**`core/collection/serializers.py`**
- Criado `EvidenciaInlineSerializer` com `id` e `arquivo_url`
- `RegistroColetaSerializer` agora expõe o campo `evidencias`

**`core/collection/views.py`**
- Queryset da listagem de coletas usa `prefetch_related('evidencias')` para evitar N+1

**`docker-compose.yml`**
- Serviço `core` recebe `MINIO_PUBLIC_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`

**`.env.example`**
- Adicionado `MINIO_PUBLIC_ENDPOINT=localhost:9000`

---

## Ação necessária

Definir no `.env` de ambos os projetos:

```
MINIO_PUBLIC_ENDPOINT=localhost:9000   # dev
# MINIO_PUBLIC_ENDPOINT=storage.seudominio.com  # prod
```

Reiniciar os containers do core e do microserviço após a alteração.
