from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario


@receiver(post_save, sender=Usuario)
def enviar_confirmacao_apos_cadastro(sender, instance, created, **kwargs):
    if not created or instance.email_confirmado:
        return
    from .tasks import enviar_email_confirmacao
    enviar_email_confirmacao.delay(instance.pk)
