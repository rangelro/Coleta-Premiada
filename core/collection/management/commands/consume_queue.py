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
                canal.queue_declare(queue='coletas', durable=True)
                canal.basic_qos(prefetch_count=1)
                canal.basic_consume(
                    queue='coletas',
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
            coleta_id = dados['coleta_id']
            self.stdout.write(f"Processando: {coleta_id}")

            # ignora se já foi processado
            if RegistroColeta.objects.filter(id_microservico=coleta_id).exists():
                self.stdout.write(f"  Duplicado ignorado: {coleta_id}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Busca o imóvel pela inscrição (identificador de domínio compartilhado
            # com o microserviço, que não conhece a PK inteira do Postgres).
            inscricao = dados.get('inscricao_imobiliaria')
            imovel = Imovel.objects.filter(inscricao=inscricao, ativo=True).first()

            if imovel is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Imóvel inscricao={inscricao} não encontrado ou inativo. "
                        f"Mensagem descartada."
                    )
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Lê a pontuação já calculada do microserviço
            pontuacao = Decimal(str(dados.get('pontuacao', 0)))

            # Aplica o teto de 40% no ciclo mensal (MM-YYYY)
            ciclo_atual = timezone.now().strftime('%m-%Y')
            saldo, _ = SaldoPontos.objects.get_or_create(
                imovel=imovel, ciclo=ciclo_atual,
                defaults={'desconto_percentual': 0}
            )
            desconto_efetivo = aplicar_teto(saldo.desconto_percentual, pontuacao)

            # Persiste o registro no PostgreSQL
            data_hora_raw = dados.get('data_hora')
            RegistroColeta.objects.create(
                id_microservico  = coleta_id,
                imovel           = imovel,
                pontuacao        = pontuacao,
                data_hora_coleta = parse_datetime(data_hora_raw) if data_hora_raw else None,
                peso_kg          = Decimal(str(dados.get('peso_total_kg', 0))),
            )

            # Atualiza o saldo do imóvel
            if desconto_efetivo > 0:
                saldo.desconto_percentual += desconto_efetivo
                saldo.save()

            self.stdout.write(
                f"  Registrado: inscricao={inscricao} (id={imovel.id}) "
                f"| {pontuacao} pts recebidos "
                f"| {desconto_efetivo}% aplicados no saldo ({ciclo_atual})"
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logger.error(f"Mensagem malformada ignorada: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            # Erros de aplicação (payload inválido, FK errada, etc.) não são
            # transientes — re-enfileirar causa loop infinito. Descarta a
            # mensagem (idealmente uma DLQ seria configurada aqui).
            logger.error(f"Erro ao processar mensagem (descartando): {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)