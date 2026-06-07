import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Geocodifica em lote imóveis sem coordenadas ou com geocodificação falha'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula o processamento sem chamar o Nominatim nem publicar na fila',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if not dry_run:
            self._verificar_rabbitmq()

        from program.models import Imovel

        pendentes = Imovel.objects.select_related('titular').filter(
            Q(latitude__isnull=True) | Q(longitude__isnull=True) | Q(geocodificacao_falhou=True)
        )
        total = pendentes.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nenhum imóvel pendente de geocodificação.'))
            return

        prefixo_modo = '[DRY-RUN] ' if dry_run else ''
        self.stdout.write(f"{prefixo_modo}Geocodificando {total} imóvel(is)...")

        if not dry_run:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent=settings.NOMINATIM_USER_AGENT)

        sucesso = 0
        falhou = 0

        for idx, imovel in enumerate(pendentes.iterator(), start=1):
            label = f"[{idx}/{total}] inscricao={imovel.inscricao}"

            if dry_run:
                self.stdout.write(f"  {label} — seria geocodificado")
                continue

            endereco = (
                f"{imovel.logradouro}, {imovel.numero}, "
                f"{imovel.bairro}, {imovel.cidade}, {imovel.cep}, Brasil"
            )

            # Nominatim exige no máximo 1 req/s
            time.sleep(1)

            try:
                from geopy.exc import GeocoderTimedOut, GeocoderServiceError
                location = geolocator.geocode(endereco, timeout=10)
            except (GeocoderTimedOut, GeocoderServiceError) as exc:
                self.stdout.write(self.style.WARNING(f"  {label} — erro temporário: {exc}"))
                logger.error(f"Erro de geocodificação (imóvel {imovel.inscricao}): {exc}")
                falhou += 1
                continue
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  {label} — erro inesperado: {exc}"))
                logger.error(f"Erro inesperado (imóvel {imovel.inscricao}): {exc}")
                falhou += 1
                continue

            if location is None:
                self.stdout.write(
                    self.style.WARNING(f"  {label} — sem resultado para '{endereco}'")
                )
                logger.warning(
                    f"Nominatim sem resultado: inscricao={imovel.inscricao}, "
                    f"endereco='{endereco}'"
                )
                Imovel.objects.filter(pk=imovel.pk).update(geocodificacao_falhou=True)
                falhou += 1
                continue

            Imovel.objects.filter(pk=imovel.pk).update(
                latitude=location.latitude,
                longitude=location.longitude,
                geocodificacao_falhou=False,
            )

            try:
                from messaging.producer import publish_morador
                publish_morador({
                    'inscricao_imobiliaria': imovel.inscricao,
                    'nome': imovel.titular.nome,
                    'cpf': imovel.titular.cpf,
                    'endereco': imovel.logradouro,
                    'numero': imovel.numero,
                    'complemento': imovel.complemento or '',
                    'bairro': imovel.bairro,
                    'latitude': float(location.latitude),
                    'longitude': float(location.longitude),
                    'ativo': imovel.ativo,
                    'acao': 'geocodificacao_concluida',
                })
            except Exception as exc:
                logger.error(f"Erro ao publicar imóvel {imovel.inscricao} na fila: {exc}")
                self.stdout.write(
                    self.style.WARNING(
                        f"  {label} — geocodificado mas falha ao publicar na fila: {exc}"
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  {label} — lat={location.latitude}, lng={location.longitude}"
                )
            )
            sucesso += 1

        if not dry_run:
            self.stdout.write(
                f"\nConcluído: {sucesso} geocodificado(s), {falhou} falha(s) de {total}."
            )

    def _verificar_rabbitmq(self):
        from messaging.connection import get_connection
        try:
            conexao = get_connection()
            conexao.close()
        except Exception as exc:
            raise CommandError(
                f"RabbitMQ não está acessível — verifique se está rodando. Detalhe: {exc}"
            )
