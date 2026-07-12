from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Contestacao


@receiver(post_save, sender=Contestacao)
def ao_criar_contestacao(sender, instance, created, **kwargs):
    if not created:
        return
    from .tasks import notificar_contestacao_criada
    notificar_contestacao_criada.delay(instance.pk)
