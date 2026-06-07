import logging
import time

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def geocodificar_imovel(self, imovel_id: int):
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    from .models import Imovel

    try:
        imovel = Imovel.objects.select_related('titular').get(pk=imovel_id)
    except Imovel.DoesNotExist:
        logger.warning(f"Imóvel {imovel_id} não encontrado para geocodificação.")
        return

    if imovel.latitude is not None and imovel.longitude is not None:
        return

    endereco = (
        f"{imovel.logradouro}, {imovel.numero}, "
        f"{imovel.bairro}, {imovel.cidade}, {imovel.cep}, Brasil"
    )

    geolocator = Nominatim(user_agent=settings.NOMINATIM_USER_AGENT)

    # Nominatim exige no máximo 1 req/s
    time.sleep(1)

    try:
        location = geolocator.geocode(endereco, timeout=10)
    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        logger.warning(f"Erro temporário na geocodificação do imóvel {imovel_id}: {exc}")
        raise self.retry(exc=exc)

    if location is None:
        logger.warning(
            f"Geocodificação sem resultado para imóvel {imovel_id} "
            f"(endereço consultado: '{endereco}')"
        )
        Imovel.objects.filter(pk=imovel_id).update(geocodificacao_falhou=True)
        return

    Imovel.objects.filter(pk=imovel_id).update(
        latitude=location.latitude,
        longitude=location.longitude,
        geocodificacao_falhou=False,
    )
    logger.info(
        f"Imóvel {imovel.inscricao} geocodificado: "
        f"lat={location.latitude}, lng={location.longitude}"
    )

    # Republica na fila com as coordenadas agora disponíveis
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
        logger.error(
            f"Erro ao republicar imóvel {imovel.inscricao} "
            f"após geocodificação: {exc}"
        )
