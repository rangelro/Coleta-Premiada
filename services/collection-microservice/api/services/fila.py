import json
import pika
import os
import logging

logger = logging.getLogger(__name__)


def publicar_pesagem(pesagem_data: dict) -> bool:
    """
    Publica uma pesagem na fila RabbitMQ.
    Retorna True em caso de sucesso, False em caso de erro.
    """
    try:
        credentials = pika.PlainCredentials(
            username=os.getenv('RABBITMQ_DEFAULT_USER', 'guest'),
            password=os.getenv('RABBITMQ_DEFAULT_PASS', 'guest'),
        )
        parametros = pika.ConnectionParameters(
            host='rabbitmq',   # nome do serviço no docker-compose
            port=5672,
            credentials=credentials,
        )

        conexao = pika.BlockingConnection(parametros)
        canal   = conexao.channel()

        # Garante que a fila existe antes de publicar
        canal.queue_declare(
            queue='pesagens',
            durable=True   # sobrevive a reinicializações do RabbitMQ
        )

        canal.basic_publish(
            exchange='',
            routing_key='pesagens',
            body=json.dumps(pesagem_data, default=str),
            properties=pika.BasicProperties(
                delivery_mode=2  # mensagem persistente em disco
            )
        )

        conexao.close()
        logger.info(f"Pesagem publicada na fila: {pesagem_data}")
        return True

    except Exception as e:
        logger.error(f"Erro ao publicar na fila: {e}")
        return False