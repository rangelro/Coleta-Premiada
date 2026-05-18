import json
import logging
import time
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from decimal import Decimal
from messaging.connection import get_connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Consome mensagens da fila RabbitMQ e registra as coletas no Core'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando consumer da fila pesagens...')

        # Retry com backoff: tenta conectar até 10x antes de desistir
        max_tentativas = 10
        for tentativa in range(1, max_tentativas + 1):
            try:
                conexao = get_connection()
                canal = conexao.channel()
                canal.queue_declare(queue='fila.pesagens', durable=True)
                canal.basic_qos(prefetch_count=1)
                canal.basic_consume(
                    queue='fila.pesagens',
                    on_message_callback=self._processar,
                )
                self.stdout.write('Aguardando mensagens. CTRL+C para sair.')
                canal.start_consuming()
                break  # se chegou aqui, saiu do consuming normalmente (ex: CTRL+C)
            except KeyboardInterrupt:
                self.stdout.write('\nEncerrando consumer.')
                break
            except Exception as e:
                espera = min(2 ** tentativa, 30)  # backoff: 2s, 4s, 8s... até 30s
                self.stdout.write(
                    self.style.WARNING(
                        f'  Tentativa {tentativa}/{max_tentativas} falhou: {e}. '
                        f'Aguardando {espera}s...'
                    )
                )
                if tentativa == max_tentativas:
                    self.stdout.write(self.style.ERROR('Máximo de tentativas atingido. Encerrando.'))
                    raise
                time.sleep(espera)

    # Processa a mensagem recebida e faz o cadastro no core
    def _processar(self, ch, method, properties, body):
        from collection.models import RegistroColeta
        from program.models import Imovel, SaldoPontos
        from program.business_rules import aplicar_teto

        try:
            dados = json.loads(body)
            self.stdout.write(f"Processando: {dados['id']}")

            # ignora se já foi processado
            if RegistroColeta.objects.filter(
                    id_microservico=dados['id']).exists():
                self.stdout.write(f"  Duplicado ignorado: {dados['id']}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Busca o imóvel pelo ID do banco de dados (chave primária)
            imovel_id = dados.get('imovel_id')
            imovel = Imovel.objects.filter(
                id=imovel_id,
                ativo=True
            ).first()

            if imovel is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Imóvel id={imovel_id} não encontrado ou inativo. "
                        f"Mensagem descartada."
                    )
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Lê a pontuação já calculada do microserviço
            pontuacao = Decimal(str(dados.get('pontuacao', 0)))

            # Aplica o teto de 40% se o imóvel estiver cadastrado
            desconto_efetivo = pontuacao
            ano_atual = timezone.now().year

            if imovel:
                saldo, _ = SaldoPontos.objects.get_or_create(
                    imovel=imovel, ciclo=ano_atual,
                    defaults={'desconto_percentual': 0}
                )
                desconto_efetivo = aplicar_teto(
                    saldo.desconto_percentual, pontuacao
                )

            # Persiste o registro no PostgreSQL
            coleta = RegistroColeta.objects.create(
                id_microservico       = dados['id'],
                imovel                = imovel,
                pontuacao             = pontuacao,
                data_hora_coleta      = parse_datetime(dados['data_hora']),
                material              = dados.get('material', ''),
                peso_kg               = Decimal(str(dados.get('peso_kg', 0)))
            )

            # Atualiza o saldo do imóvel
            if imovel and desconto_efetivo > 0:
                saldo.desconto_percentual += desconto_efetivo
                saldo.save()

            self.stdout.write(
                f"  Registrado: imovel_id={imovel_id} "
                f"| {pontuacao} recebidos "
                f"| {desconto_efetivo}% aplicados no saldo"
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logger.error(f"Mensagem malformada ignorada: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)