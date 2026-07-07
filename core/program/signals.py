import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Imovel

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Imovel)
def publicar_imovel(sender, instance, created, **kwargs):
    """
    Sinal do Django disparado automaticamente após a criação ou atualização de um Imóvel.
    Publica os dados do imóvel (incluindo o número de moradores) no RabbitMQ para
    sincronização automática com o banco MongoDB do microsserviço de coletas.
    """
    try:
        from messaging.producer import publish_morador
        publish_morador({
            'inscricao_imobiliaria': instance.inscricao,
            'proprietario_id': instance.titular_id,
            'nome': instance.titular.nome,
            'cpf': instance.titular.cpf,
            'endereco': instance.logradouro,
            'numero': instance.numero,
            'complemento': instance.complemento or '',
            'bairro': instance.bairro,
            'latitude': float(instance.latitude) if instance.latitude is not None else None,
            'longitude': float(instance.longitude) if instance.longitude is not None else None,
            'ativo': instance.ativo,
            'num_moradores': instance.num_moradores,
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
