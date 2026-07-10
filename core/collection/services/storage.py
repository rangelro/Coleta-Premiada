import uuid
import os
from django.conf import settings
from minio import Minio

def _client() -> Minio:
    endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
    return Minio(
        endpoint,
        access_key=os.getenv('MINIO_ROOT_USER', 'minio_admin'),
        secret_key=os.getenv('MINIO_ROOT_PASSWORD', 'troque_esta_senha'),
        secure=os.getenv('MINIO_USE_HTTPS', 'False') == 'True',
    )

import json

def _garantir_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    
    # Garante que a politica seja de leitura pública para as fotos carregarem no front
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
    """Faz upload de um arquivo para o MinIO e retorna a URL pública do objeto."""
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

    protocol = 'https' if os.getenv('MINIO_USE_HTTPS', 'False') == 'True' else 'http'
    endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
    # Use localhost if we are generating url to send to client? Actually the front is running on localhost.
    # The URL needs to be accessible by the browser! 
    # Usually we use localhost:9000 for browser if the minio container port maps to it.
    if 'minio' in endpoint:
        endpoint = endpoint.replace('minio', 'localhost')
    return f"{protocol}://{endpoint}/{bucket}/{object_name}"
