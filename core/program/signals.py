import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Imovel

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Imovel)
def publicar_imovel(sender, instance, created, **kwargs):
    try:
        from messaging.producer import publish_morador
        publish_morador({
            'inscricao_imobiliaria': instance.inscricao,
            'nome': instance.titular.nome,
            'cpf': instance.titular.cpf,
            'endereco': instance.logradouro,
            'numero': instance.numero,
            'complemento': instance.complemento or '',
            'bairro': instance.bairro,
            'latitude': float(instance.latitude) if instance.latitude is not None else None,
            'longitude': float(instance.longitude) if instance.longitude is not None else None,
            'ativo': instance.ativo,
            'acao': 'adesao_programa' if created else 'atualizacao_imovel',
        })
        acao_log = 'criação' if created else 'atualização'
        logger.info(f"Imóvel publicado na fila ({acao_log}): {instance.inscricao}")
    except Exception as e:
        logger.error(f"Erro ao publicar imóvel {instance.inscricao} na fila: {e}")

    # Agenda geocodificação somente se coordenadas ausentes e sem falha registrada
    if (
        instance.latitude is None
        and instance.longitude is None
        and not instance.geocodificacao_falhou
    ):
        try:
            from .tasks import geocodificar_imovel
            geocodificar_imovel.delay(instance.pk)
            logger.info(f"Geocodificação agendada para imóvel: {instance.inscricao}")
        except Exception as e:
            logger.error(
                f"Erro ao agendar geocodificação do imóvel {instance.inscricao}: {e}"
            )
