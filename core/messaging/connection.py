import os
import pika

def get_connection():
    credentials = pika.PlainCredentials(
        os.getenv('RABBITMQ_DEFAULT_USER', 'guest'),
        os.getenv('RABBITMQ_DEFAULT_PASS', 'guest'),
    )
    
    host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    
    # Configura a conexão
    params = pika.ConnectionParameters(
        host=host,
        port=5672,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(params)
