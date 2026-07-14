import uuid
import os
import logging
from django.conf import settings
from minio import Minio

logger = logging.getLogger(__name__)

def _client() -> Minio:
    endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
    # Tenta ambos os padrões de credenciais (compatível com microserviço e docker-compose)
    access_key = os.getenv('MINIO_ACCESS_KEY') or os.getenv('MINIO_ROOT_USER', 'minioadmin')
    secret_key = os.getenv('MINIO_SECRET_KEY') or os.getenv('MINIO_ROOT_PASSWORD', 'minioadmin')
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=os.getenv('MINIO_USE_HTTPS', 'False').lower() == 'true',
    )

import json

def _garantir_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"]
                }
            ]
        }
        client.set_bucket_policy(bucket, json.dumps(policy))

def upload_arquivo(file_obj, content_type: str = 'image/jpeg', folder: str = 'evidencias') -> str:
    """Faz upload de um arquivo para o MinIO e retorna o object key (path relativo)."""
    ext = content_type.split('/')[-1] if '/' in content_type else 'jpg'
    ext = ext.replace('jpeg', 'jpg')
    object_name = f"{folder}/{uuid.uuid4()}.{ext}"

    client = _client()
    bucket = os.getenv('MINIO_BUCKET_NAME', 'coletas')
    _garantir_bucket(client, bucket)

    client.put_object(
        bucket,
        object_name,
        file_obj,
        length=file_obj.size,
        content_type=content_type,
    )

    return object_name


def get_arquivo_stream(object_key: str):
    """Busca um objeto no MinIO e retorna (stream, content_type, size)."""
    client = _client()
    bucket = os.getenv('MINIO_BUCKET_NAME', 'coletas')

    def _try_get(key):
        try:
            stat = client.stat_object(bucket, key)
            response = client.get_object(bucket, key)
            return response, stat.content_type, stat.size
        except Exception:
            return None, None, None

    # Tenta a chave como está
    stream, ct, size = _try_get(object_key)
    if stream:
        return stream, ct, size

    # Fallback: dados antigos podem ter prefixo do bucket duplicado
    # ex: "coletas/coletas/uuid.jpg" em vez de "coletas/uuid.jpg"
    bucket_prefix = bucket + '/'
    if object_key.startswith(bucket_prefix):
        stripped = object_key[len(bucket_prefix):]
        stream, ct, size = _try_get(stripped)
        if stream:
            logger.info(f"MinIO: chave legacy corrigida: {object_key} -> {stripped}")
            return stream, ct, size

    logger.error(f"MinIO get_object falhou: bucket={bucket}, key={object_key}")
    return None, None, None


def get_public_url(object_key: str) -> str:
    """Retorna a URL pública direta do MinIO (fallback, se proxy não for usado)."""
    protocol = 'https' if os.getenv('MINIO_USE_HTTPS', 'False') == 'True' else 'http'
    public_endpoint = os.getenv('MINIO_PUBLIC_ENDPOINT', os.getenv('MINIO_ENDPOINT', 'localhost:9000'))
    bucket = os.getenv('MINIO_BUCKET_NAME', 'coletas')
    return f"{protocol}://{public_endpoint}/{bucket}/{object_key}"
