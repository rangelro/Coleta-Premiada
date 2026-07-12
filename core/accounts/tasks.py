import logging

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_email_confirmacao(self, usuario_id: int):
    from .models import Usuario
    from .utils import gerar_token_confirmacao

    try:
        usuario = Usuario.objects.get(pk=usuario_id)
    except Usuario.DoesNotExist:
        logger.warning("enviar_email_confirmacao: usuário %s não encontrado.", usuario_id)
        return

    if usuario.email_confirmado:
        logger.info("enviar_email_confirmacao: usuário %s já confirmado, ignorando.", usuario_id)
        return

    token = gerar_token_confirmacao(usuario)
    link = f"{settings.FRONTEND_BASE_URL}/confirmar-email?token={token}"

    logger.info(
        "enviar_email_confirmacao: enviando para %s via backend=%s",
        usuario.email,
        settings.EMAIL_BACKEND,
    )

    try:
        send_mail(
            subject='Confirme seu e-mail — Coleta Premiada',
            message=(
                f"Olá, {usuario.nome}!\n\n"
                f"Clique no link abaixo para confirmar seu e-mail (válido por 24h):\n{link}\n\n"
                "Se não criou uma conta, ignore este e-mail."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            fail_silently=False,
        )
        logger.info("enviar_email_confirmacao: e-mail enviado com sucesso para %s.", usuario.email)
    except Exception as exc:
        logger.error(
            "enviar_email_confirmacao: falha ao enviar para %s — %s. Tentativa %s/%s.",
            usuario.email, exc, self.request.retries + 1, self.max_retries + 1,
        )
        raise self.retry(exc=exc)
