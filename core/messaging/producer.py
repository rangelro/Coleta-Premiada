import json
import logging
import pika
from .connection import get_connection

logger = logging.getLogger(__name__)

# Função para publicar mensagem na fila
def publish_message(queue_name: str, payload: dict):
    """
    Publica uma mensagem em uma fila direta.
    """
    try:
        conexao = get_connection()
        canal = conexao.channel()
        
        # Garante que a fila exista
        canal.queue_declare(queue=queue_name, durable=True)
        
        canal.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )
        logger.info(f"Mensagem publicada na fila '{queue_name}': {payload}")
        
        conexao.close()
    except Exception as e:
        logger.error(f"Erro ao publicar na fila '{queue_name}': {e}")
        raise

# Função para publicar adesão de morador no RabbitMQ
def publish_morador(morador_data: dict):
    """
    O Core publica quando um morador faz adesão via API.
    """
    publish_message('fila.moradores', morador_data)
