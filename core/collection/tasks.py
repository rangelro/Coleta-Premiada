import logging

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notificar_contestacao_criada(self, contestacao_id: int):
    from .models import Contestacao
    from accounts.models import Usuario

    try:
        contestacao = Contestacao.objects.select_related(
            'coleta__imovel__cidade', 'coleta__imovel__titular'
        ).get(pk=contestacao_id)
    except Contestacao.DoesNotExist:
        logger.warning("notificar_contestacao_criada: contestação %s não encontrada.", contestacao_id)
        return

    cidade = contestacao.coleta.imovel.cidade
    morador = contestacao.coleta.imovel.titular
    inscricao = contestacao.coleta.imovel.inscricao

    destinatarios = list(
        Usuario.objects.filter(
            perfil__in=['gestor', 'supervisor'],
            cidade=cidade,
            ativo=True,
            email_confirmado=True,
        ).values_list('email', flat=True)
    )

    if not destinatarios:
        logger.info(
            "notificar_contestacao_criada: sem destinatários para cidade '%s', abortando.",
            cidade,
        )
        return

    link = f"{settings.FRONTEND_BASE_URL}/contestacoes/{contestacao_id}"

    logger.info(
        "notificar_contestacao_criada: notificando %d destinatário(s) sobre contestação %s.",
        len(destinatarios), contestacao_id,
    )

    try:
        send_mail(
            subject=f'Nova contestação — Imóvel {inscricao}',
            message=(
                f"Uma contestação foi aberta pelo morador {morador.nome}.\n\n"
                f"Imóvel: {inscricao}\n"
                f"Motivo: {contestacao.motivo}\n\n"
                f"Acesse para analisar: {link}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )
        logger.info("notificar_contestacao_criada: e-mails enviados com sucesso.")
    except Exception as exc:
        logger.error("notificar_contestacao_criada: falha no envio — %s. Tentativa %s/%s.",
                     exc, self.request.retries + 1, self.max_retries + 1)
        raise self.retry(exc=exc)
