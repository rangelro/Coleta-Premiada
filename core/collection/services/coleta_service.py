import uuid
import logging
from decimal import Decimal
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from collection.models import RegistroColeta
from program.models import Imovel, Programa, RegraPrograma, SaldoPontos, ConstantePontuacao, Ciclo
from program.business_rules import aplicar_teto
from collection.services.storage import upload_arquivo

logger = logging.getLogger(__name__)

def registrar_nova_coleta(
    imovel: Imovel,
    peso_kg: Decimal,
    data_hora,
    id_microservico: str = None,
    registrado_por = None,
    foto_file = None,
    foto_url: str = ''
) -> RegistroColeta:
    """
    Serviço centralizado para registrar uma coleta.
    Calcula pontos, atualiza saldo do morador e salva a coleta.
    
    Se id_microservico for None (ex: coleta manual pelo painel), autogera um UUID.
    Se foto_file for fornecido, faz upload para o MinIO e armazena o object key.
    Se foto_url for fornecida (vinda do microserviço), armazena o object key extraído.
    """
    is_manual = False
    if not id_microservico:
        id_microservico = f"MANUAL-{uuid.uuid4()}"
        is_manual = True

    # Ignora se já existe pelo id_microservico
    if RegistroColeta.objects.filter(id_microservico=id_microservico).exists():
        logger.warning(f"Coleta duplicada ignorada: {id_microservico}")
        return RegistroColeta.objects.get(id_microservico=id_microservico)

    # Resolve o programa ativo na data da coleta
    hoje = timezone.now().date()
    programa = Programa.objects.filter(
        ativo=True, data_inicio__lte=hoje, data_fim__gte=hoje,
    ).first()

    if programa is None:
        logger.warning(f"Nenhum programa ativo em {hoje}. Coleta {id_microservico} sem programa/saldo.")

    # Calcula pontuação localmente: peso × constante configurável
    constante = ConstantePontuacao.get_valor()
    pontos_por_kg = Decimal(str(constante.pontos_por_kg))
    pontuacao = (peso_kg * pontos_por_kg).quantize(Decimal('0.01'))

    # Se a data for string, formata, senao usa direto (ou timezone.now)
    if isinstance(data_hora, str):
        data_hora = parse_datetime(data_hora)
    if not data_hora:
        data_hora = timezone.now()

    # Resolve foto
    object_key = foto_url
    if foto_file:
        try:
            object_key = upload_arquivo(foto_file, content_type=foto_file.content_type)
        except Exception as e:
            logger.error(f"Erro ao fazer upload da foto da coleta {id_microservico}: {e}")

    # Persiste o registro no PostgreSQL
    coleta = RegistroColeta.objects.create(
        id_microservico=id_microservico,
        imovel=imovel,
        programa=programa,
        pontuacao=pontuacao,
        data_hora_coleta=data_hora,
        peso_kg=peso_kg,
        foto_url=object_key,
        registrado_por=registrado_por
    )

    # Atualiza o saldo do imóvel apenas quando há programa e ciclo ativos
    if programa is not None:
        hoje = data_hora.date() if data_hora else timezone.now().date()
        ciclo = Ciclo.objects.filter(
            programa=programa,
            data_inicio__lte=hoje,
            data_fim__gte=hoje,
            status='aberto'
        ).first()

        if ciclo:
            regras, _ = RegraPrograma.objects.get_or_create(programa=programa)
            saldo, _ = SaldoPontos.objects.get_or_create(
                imovel=imovel, programa=programa, ciclo=ciclo,
                defaults={'desconto_percentual': 0}
            )
            # Converte pontos em percentual de desconto antes de aplicar o teto
            novo_desconto = (pontuacao / regras.pontos_por_real).quantize(Decimal('0.01'))
            desconto_efetivo = aplicar_teto(saldo.desconto_percentual, novo_desconto)
            
            if desconto_efetivo > 0:
                saldo.desconto_percentual = (saldo.desconto_percentual + desconto_efetivo).quantize(Decimal('0.01'))
                saldo.save()
        else:
            logger.warning(f"Nenhum ciclo aberto em {hoje} para o programa {programa.nome}. Saldo não atualizado.")

    return coleta
