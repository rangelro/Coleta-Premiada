from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario


@receiver(post_save, sender=Usuario)
def enviar_confirmacao_apos_cadastro(sender, instance, created, **kwargs):
    # Apenas moradores que se cadastram publicamente precisam confirmar e-mail.
    # Gestor/supervisor/gerente_geral são criados pelo admin e recebem o convite
    # via enviar_email_convite (chamado explicitamente no serializer de criação).
    if not created or instance.email_confirmado or instance.perfil != 'morador':
        return
    from .tasks import enviar_email_confirmacao
    enviar_email_confirmacao.delay(instance.pk)
