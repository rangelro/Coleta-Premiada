import logging
import time

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notificar_fim_ciclo(self, ciclo_id: int):
    from .models import Ciclo
    from accounts.models import Usuario

    try:
        ciclo = Ciclo.objects.select_related('programa').get(pk=ciclo_id)
    except Ciclo.DoesNotExist:
        logger.warning("notificar_fim_ciclo: ciclo %s não encontrado.", ciclo_id)
        return

    destinatarios = list(
        Usuario.objects.filter(
            perfil__in=['gestor', 'supervisor'],
            ativo=True,
            email_confirmado=True,
        ).values_list('email', flat=True)
    )

    if not destinatarios:
        logger.info("notificar_fim_ciclo: sem destinatários, abortando.")
        return

    link = f"{settings.FRONTEND_BASE_URL}/ciclos/{ciclo_id}"

    logger.info("notificar_fim_ciclo: notificando %d destinatário(s) sobre ciclo %s.",
                len(destinatarios), ciclo_id)

    try:
        send_mail(
            subject=f'Ciclo encerrado — {ciclo.nome}',
            message=(
                f"O ciclo '{ciclo.nome}' do programa '{ciclo.programa.nome}' foi encerrado.\n\n"
                f"Período: {ciclo.data_inicio:%d/%m/%Y} a {ciclo.data_fim:%d/%m/%Y}\n\n"
                f"Acesse para ver os resultados: {link}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )
        logger.info("notificar_fim_ciclo: e-mails enviados com sucesso.")
    except Exception as exc:
        logger.error("notificar_fim_ciclo: falha no envio — %s. Tentativa %s/%s.",
                     exc, self.request.retries + 1, self.max_retries + 1)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notificar_fim_programa(self, programa_id: int):
    from .models import Programa
    from accounts.models import Usuario

    try:
        programa = Programa.objects.get(pk=programa_id)
    except Programa.DoesNotExist:
        logger.warning("notificar_fim_programa: programa %s não encontrado.", programa_id)
        return

    staff = list(
        Usuario.objects.filter(
            perfil__in=['gestor', 'supervisor'],
            ativo=True,
            email_confirmado=True,
        ).values_list('email', flat=True)
    )

    moradores = list(
        Usuario.objects.filter(
            perfil='morador',
            ativo=True,
            email_confirmado=True,
            imoveis__programa=programa,
        ).distinct().values_list('email', flat=True)
    )

    todos = list(set(staff + moradores))
    if not todos:
        logger.info("notificar_fim_programa: sem destinatários, abortando.")
        return

    logger.info("notificar_fim_programa: notificando %d destinatário(s) sobre programa %s.",
                len(todos), programa_id)

    try:
        send_mail(
            subject=f'Programa encerrado — {programa.nome}',
            message=(
                f"O programa '{programa.nome}' foi encerrado.\n\n"
                f"Período: {programa.data_inicio:%d/%m/%Y} a {programa.data_fim:%d/%m/%Y}\n\n"
                "Obrigado pela participação!"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=todos,
            fail_silently=False,
        )
        logger.info("notificar_fim_programa: e-mails enviados com sucesso.")
    except Exception as exc:
        logger.error("notificar_fim_programa: falha no envio — %s. Tentativa %s/%s.",
                     exc, self.request.retries + 1, self.max_retries + 1)
        raise self.retry(exc=exc)
