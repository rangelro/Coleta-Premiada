import secrets
from django.utils import timezone
from datetime import timedelta


def gerar_token_confirmacao(usuario):
    token = secrets.token_urlsafe(48)
    usuario.token_confirmacao = token
    usuario.token_expira_em = timezone.now() + timedelta(hours=24)
    usuario.save(update_fields=['token_confirmacao', 'token_expira_em'])
    return token
