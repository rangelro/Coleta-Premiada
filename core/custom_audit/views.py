"""
Class-Based Views do app `custom_audit`.

Cobre:
- /logs           consulta paginada do histórico de auditoria (somente gestor)
- /logs/export    exportação do histórico de auditoria filtrado (somente gestor)
"""
import csv
import datetime
import json

from django.http import StreamingHttpResponse
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from accounts.permissions import IsGestor
from accounts.scoping import escopar_por_cidade
from config.pagination import StandardResultsSetPagination

from .models import AuditLog
from .serializers import AuditLogSerializer

OPERACOES_VALIDAS = {choice[0] for choice in AuditLog.OPERACAO_CHOICES}


def filtrar_audit_logs(params, user):
    """
    Aplica os filtros suportados por /logs e /logs/export a partir dos
    query params da requisição: usuario_id, tabela, operacao, data_inicio,
    data_fim, objeto_id e cidade (este último só tem efeito para gerente_geral).
    """
    qs = AuditLog.objects.all()
    qs = escopar_por_cidade(qs, user, 'cidade')

    usuario_id = params.get('usuario_id')
    if usuario_id:
        try:
            qs = qs.filter(usuario_id=int(usuario_id))
        except ValueError:
            raise ValidationError({'usuario_id': 'Deve ser um número inteiro.'})

    tabela = params.get('tabela')
    if tabela:
        qs = qs.filter(tabela=tabela)

    operacao = params.get('operacao')
    if operacao:
        operacao = operacao.upper()
        if operacao not in OPERACOES_VALIDAS:
            raise ValidationError({
                'operacao': f'Deve ser uma das opções: {", ".join(sorted(OPERACOES_VALIDAS))}.'
            })
        qs = qs.filter(operacao=operacao)

    objeto_id = params.get('objeto_id')
    if objeto_id:
        qs = qs.filter(objeto_id=objeto_id)

    data_inicio = params.get('data_inicio')
    if data_inicio:
        try:
            datetime.date.fromisoformat(data_inicio)
        except ValueError:
            raise ValidationError({'data_inicio': 'Use o formato YYYY-MM-DD.'})
        qs = qs.filter(timestamp__date__gte=data_inicio)

    data_fim = params.get('data_fim')
    if data_fim:
        try:
            datetime.date.fromisoformat(data_fim)
        except ValueError:
            raise ValidationError({'data_fim': 'Use o formato YYYY-MM-DD.'})
        qs = qs.filter(timestamp__date__lte=data_fim)

    cidade = params.get('cidade')
    if cidade and getattr(user, 'perfil', None) == 'gerente_geral':
        qs = qs.filter(cidade=cidade)

    return qs


# ---------------------------------------------------------------------------
# LOGS DE AUDITORIA  /logs
# ---------------------------------------------------------------------------
class AuditLogListView(generics.ListAPIView):
    """
    🔒 GET /logs — lista e filtra o histórico de auditoria (somente gestor).

    Filtros suportados via query params: usuario_id, tabela, operacao,
    data_inicio, data_fim, objeto_id. Paginação obrigatória (máx. 100/página).
    """
    permission_classes = [IsGestor]
    serializer_class = AuditLogSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return filtrar_audit_logs(self.request.query_params, self.request.user)


# ---------------------------------------------------------------------------
# EXPORTAÇÃO  /logs/export
# ---------------------------------------------------------------------------
class _Echo:
    """Objeto tipo arquivo que apenas repassa o valor escrito, usado pelo csv.writer em streaming."""

    def write(self, value):
        return value


CSV_HEADER = [
    'id', 'timestamp', 'usuario_id', 'usuario_email', 'operacao',
    'tabela', 'objeto_id', 'dados_antes', 'dados_depois', 'ip_origem', 'endpoint', 'cidade',
]


def gerar_linhas_csv(queryset):
    writer = csv.writer(_Echo())
    yield writer.writerow(CSV_HEADER)
    for log in queryset.iterator():
        yield writer.writerow([
            log.id,
            log.timestamp.isoformat(),
            log.usuario_id,
            log.usuario_email,
            log.operacao,
            log.tabela,
            log.objeto_id,
            json.dumps(log.dados_antes, ensure_ascii=False) if log.dados_antes is not None else '',
            json.dumps(log.dados_depois, ensure_ascii=False) if log.dados_depois is not None else '',
            log.ip_origem,
            log.endpoint,
            log.cidade,
        ])


class AuditLogExportView(APIView):
    """
    🔒 GET /logs/export?formato=csv — exporta o histórico de auditoria
    filtrado (mesmos filtros de /logs) em CSV (somente gestor).
    """
    permission_classes = [IsGestor]

    def get(self, request):
        formato = request.query_params.get('formato', 'csv').lower()
        if formato != 'csv':
            raise ValidationError({'formato': 'Apenas o formato "csv" é suportado.'})

        queryset = filtrar_audit_logs(request.query_params, request.user)

        response = StreamingHttpResponse(gerar_linhas_csv(queryset), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
        return response
