import logging
from typing import Callable
from .connection import get_connection

logger = logging.getLogger(__name__)

def consume_queue(queue_name: str, callback: Callable):
    """
    Consome mensagens das filas
    """
    try:
        conexao = get_connection()
        canal = conexao.channel()
        
        # Garante que a fila existe
        canal.queue_declare(queue=queue_name, durable=True)
        canal.basic_qos(prefetch_count=1)
        
        # callback recebe a mensagem e processa
        canal.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
        )
        
        logger.info(f"Aguardando mensagens na fila '{queue_name}'...")
        canal.start_consuming()
    except Exception as e:
        logger.error(f"Erro ao consumir da fila '{queue_name}': {e}")
        raise

