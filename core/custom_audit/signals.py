import json
import logging
from django.db.models.signals import pre_save, post_save, post_delete
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from program.models import Imovel, Programa, SaldoPontos, Consolidacao, ConstantePontuacao, RegraPrograma
from collection.models import RegistroColeta, Evidencia, Contestacao
from accounts.models import Role
from .request_store import get_current_request, get_client_ip

logger = logging.getLogger(__name__)


def serialize_model(instance):
    """
    Serializa os campos do model do Django em um dicionário de tipos serializáveis em JSON.
    """
    data = {}
    for field in instance._meta.fields:
        value = field.value_from_object(instance)
        try:
            # Tenta converter o valor serializado de volta para garantir tipos primitivos JSON limpos
            data[field.name] = json.loads(json.dumps(value, cls=DjangoJSONEncoder))
        except Exception:
            data[field.name] = str(value)
    return data


def keep_old_state(sender, instance, **kwargs):
    """
    Salva o estado da instância antes do salvamento para que possa ser registrado no post_save.
    """
    if instance.pk:
        try:
            # Consulta o banco para obter o estado atual antes que as alterações sejam confirmadas
            old_instance = sender.objects.filter(pk=instance.pk).first()
            if old_instance:
                instance._old_serialized = serialize_model(old_instance)
            else:
                instance._old_serialized = None
        except Exception as e:
            logger.warning(f"Erro ao preservar o estado pré-save de {sender.__name__} (ID: {instance.pk}): {e}")
            instance._old_serialized = None
    else:
        instance._old_serialized = None


def log_save(sender, instance, created, **kwargs):
    """
    Registra logs para operações de INSERT (created=True) e UPDATE (created=False).
    """
    from .models import AuditLog

    if sender == AuditLog:
        return

    request = get_current_request()
    usuario_id = None
    usuario_email = None
    ip_origem = None
    endpoint = None

    if request:
        user = request.user
        if user and not user.is_anonymous:
            usuario_id = user.id
            usuario_email = user.email
        ip_origem = get_client_ip(request)
        endpoint = request.path

    operacao = 'INSERT' if created else 'UPDATE'
    tabela = sender._meta.db_table
    objeto_id = str(instance.pk) if instance.pk else None
    
    dados_antes = getattr(instance, '_old_serialized', None)
    dados_depois = serialize_model(instance)

    try:
        AuditLog.objects.create(
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            operacao=operacao,
            tabela=tabela,
            objeto_id=objeto_id,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
            ip_origem=ip_origem,
            endpoint=endpoint
        )
    except Exception as e:
        logger.error(f"Falha ao criar o AuditLog no salvamento de {sender.__name__} (ID: {objeto_id}): {e}")


def log_delete(sender, instance, **kwargs):
    """
    Registra logs para operações de DELETE.
    """
    from .models import AuditLog

    if sender == AuditLog:
        return

    request = get_current_request()
    usuario_id = None
    usuario_email = None
    ip_origem = None
    endpoint = None

    if request:
        user = request.user
        if user and not user.is_anonymous:
            usuario_id = user.id
            usuario_email = user.email
        ip_origem = get_client_ip(request)
        endpoint = request.path

    operacao = 'DELETE'
    tabela = sender._meta.db_table
    objeto_id = str(instance.pk) if instance.pk else None
    
    dados_antes = serialize_model(instance)
    dados_depois = None

    try:
        AuditLog.objects.create(
            usuario_id=usuario_id,
            usuario_email=usuario_email,
            operacao=operacao,
            tabela=tabela,
            objeto_id=objeto_id,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
            ip_origem=ip_origem,
            endpoint=endpoint
        )
    except Exception as e:
        logger.error(f"Falha ao criar o AuditLog na exclusão de {sender.__name__} (ID: {objeto_id}): {e}")


def register_signals():
    Usuario = get_user_model()

    models_to_audit = [
        Usuario, Role,
        Imovel, Programa, RegraPrograma, SaldoPontos, Consolidacao, ConstantePontuacao,
        RegistroColeta, Evidencia, Contestacao,
    ]

    for model in models_to_audit:
        pre_save.connect(keep_old_state, sender=model, dispatch_uid=f"audit_pre_save_{model._meta.label}")
        post_save.connect(log_save, sender=model, dispatch_uid=f"audit_post_save_{model._meta.label}")
        post_delete.connect(log_delete, sender=model, dispatch_uid=f"audit_post_delete_{model._meta.label}")
