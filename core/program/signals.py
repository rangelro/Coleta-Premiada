import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Imovel

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Imovel)
def publicar_adesao_programa(sender, instance, created, **kwargs):
    """
    Signal disparado após salvar um Imovel.

    Quando um imóvel é CRIADO (pela API, pelo Admin ou por qualquer outro meio),
    publica automaticamente uma mensagem na fila `fila.moradores` para notificar
    outros sistemas sobre a nova adesão ao programa.
    """
    if not created:
        return  # só publica na criação, não em updates

    try:
        from messaging.producer import publish_morador
        publish_morador({
            'inscricao_imobiliaria': instance.inscricao,
            'nome': instance.titular.nome,
            'cpf': instance.titular.cpf,
            'endereco': f"{instance.logradouro}, {instance.numero} - {instance.bairro}",
            'acao': 'adesao_programa',
        })
        logger.info(f"Adesão publicada na fila para o imóvel {instance.inscricao}")
    except Exception as e:
        # Falha na fila NÃO deve reverter o salvamento do imóvel.
        logger.error(f"Erro ao publicar adesão do imóvel {instance.inscricao} na fila: {e}")
