import json
import pika
import os
import logging
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Consome mensagens da fila RabbitMQ e registra coletas no Core'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando consumer da fila pesagens...')

        credentials = pika.PlainCredentials(
            os.getenv('RABBITMQ_DEFAULT_USER', 'guest'),
            os.getenv('RABBITMQ_DEFAULT_PASS', 'guest'),
        )
        params = pika.ConnectionParameters(
            host='rabbitmq', port=5672, credentials=credentials,
            heartbeat=600, blocked_connection_timeout=300,
        )

        conexao = pika.BlockingConnection(params)
        canal = conexao.channel()
        canal.queue_declare(queue='pesagens', durable=True)
        canal.basic_qos(prefetch_count=1)
        canal.basic_consume(
            queue='pesagens',
            on_message_callback=self._processar,
        )

        self.stdout.write('Aguardando mensagens. CTRL+C para sair.')
        canal.start_consuming()

    def _processar(self, ch, method, properties, body):
        from collection.models import RegistroColeta
        from program.models import Imovel, SaldoPontos
        from program.business_rules import (
            calcular_desconto, aplicar_teto, DESCONTO_MAXIMO,
        )

        try:
            dados = json.loads(body)
            self.stdout.write(f"Processando: {dados['id']}")

            # Idempotência — ignora se já foi processado
            if RegistroColeta.objects.filter(
                    id_microservico=dados['id']).exists():
                self.stdout.write(f"  Duplicado ignorado: {dados['id']}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Busca o imóvel pelo número de inscrição
            imovel = Imovel.objects.filter(
                inscricao=dados['inscricao_imobiliaria'],
                ativo=True
            ).first()

            # Calcula desconto com base nas regras de negócio
            num_moradores = imovel.num_moradores if imovel else 1
            peso = Decimal(dados['peso_kg'])

            desconto_bruto = calcular_desconto(
                peso, dados['material'], num_moradores
            )

            # Aplica o teto de 40% se o imóvel estiver cadastrado
            desconto_efetivo = desconto_bruto
            ano_atual = timezone.now().year

            if imovel:
                saldo, _ = SaldoPontos.objects.get_or_create(
                    imovel=imovel, ciclo=ano_atual,
                    defaults={'desconto_percentual': 0, 'total_kg': 0}
                )
                desconto_efetivo = aplicar_teto(
                    saldo.desconto_percentual, desconto_bruto
                )

            # Persiste o registro no PostgreSQL
            coleta = RegistroColeta.objects.create(
                id_microservico       = dados['id'],
                imovel                = imovel,
                inscricao_imobiliaria = dados['inscricao_imobiliaria'],
                material              = dados['material'],
                peso_kg               = peso,
                agente_id             = dados['agente_id'],
                desconto_gerado       = desconto_efetivo,
                data_hora_coleta      = parse_datetime(dados['data_hora']),
            )

            # Atualiza o saldo do imóvel
            if imovel and desconto_efetivo > 0:
                saldo.desconto_percentual += desconto_efetivo
                saldo.total_kg += peso
                saldo.save()

            self.stdout.write(
                f"  Registrado: {coleta.inscricao_imobiliaria} "
                f"| {dados['material']} | {peso}kg "
                f"| {desconto_efetivo}% desconto"
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)