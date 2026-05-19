import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Imovel

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Imovel)
def publicar_imovel(sender, instance, created, **kwargs):
    """
    Signal disparado após salvar um Imovel.

    Publica na fila `imoveis` tanto na criação quanto na atualização,
    para manter o microserviço de coleta sincronizado.
    """
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
            'ativo': instance.ativo,
            'acao': 'adesao_programa' if created else 'atualizacao_imovel',
        })
        acao_log = 'criação' if created else 'atualização'
        logger.info(f"Imóvel publicado na fila ({acao_log}): {instance.inscricao}")
    except Exception as e:
        # Falha na fila NÃO deve reverter o salvamento do imóvel.
        logger.error(f"Erro ao publicar imóvel {instance.inscricao} na fila: {e}")
