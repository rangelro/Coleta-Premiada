import datetime
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsGestor
from accounts.scoping import escopar_por_cidade
from config.pagination import StandardResultsSetPagination

from .models import RelatorioLLM
from .serializers import RelatorioLLMRequestSerializer, RelatorioLLMSerializer

logger = logging.getLogger(__name__)


def _as_aware_datetime(d: datetime.date, end_of_day: bool = False) -> datetime.datetime:
    t = datetime.time.max if end_of_day else datetime.time.min
    return timezone.make_aware(datetime.datetime.combine(d, t))


class GenerateReportView(APIView):
    """
    POST /api/reports/generate

    Cria o registro do relatório imediatamente com status 'pendente'
    e dispara tarefa Celery para geração assíncrona via LLM.
    Apenas gestores e gerente_geral podem acessar.
    """
    permission_classes = [IsGestor]

    def post(self, request):
        serializer = RelatorioLLMRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo = serializer.validated_data['tipo']
        periodo = serializer.validated_data['periodo']
        programa_id = serializer.validated_data.get('programa_id')
        direcionamento = serializer.validated_data.get('direcionamento', '')

        relatorio = RelatorioLLM.objects.create(
            tipo=tipo,
            periodo_inicio=periodo['inicio'],
            periodo_fim=periodo['fim'],
            programa_id=programa_id,
            direcionamento=direcionamento,
            status='pendente',
            gerado_por=request.user,
        )

        try:
            from .tasks import gerar_relatorio_async
            gerar_relatorio_async.delay(relatorio.id)
        except Exception as e:
            logger.error("Falha ao despachar task Celery para relatório id=%s: %s", relatorio.id, e)
            relatorio.status = 'erro'
            relatorio.relatorio = f"Erro ao despachar geração: serviço de processamento indisponível."
            relatorio.save(update_fields=['status', 'relatorio'])

        return Response(RelatorioLLMSerializer(relatorio).data, status=status.HTTP_201_CREATED)


class ReportDetailView(generics.RetrieveAPIView):
    """
    GET /api/reports/<id>

    Retorna o detalhe de um relatório (útil para polling de status/conteúdo).
    Apenas gestores e gerente_geral podem acessar.
    """
    permission_classes = [IsGestor]
    serializer_class = RelatorioLLMSerializer

    def get_queryset(self):
        return escopar_por_cidade(
            RelatorioLLM.objects.select_related('programa', 'gerado_por'),
            self.request.user,
            'gerado_por__cidade__nome',
        )


class ReportHistoryView(generics.ListAPIView):
    """
    GET /api/reports/history

    Lista todos os relatórios gerados (paginado), escopados por cidade.
    Gestor vê apenas relatórios de usuários da sua cidade;
    gerente_geral vê todos.
    """
    permission_classes = [IsGestor]
    serializer_class = RelatorioLLMSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = escopar_por_cidade(
            RelatorioLLM.objects.select_related('programa', 'gerado_por').order_by('-gerado_em'),
            self.request.user,
            'gerado_por__cidade__nome',
        )

        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)

        programa_id = self.request.query_params.get('programa_id')
        if programa_id:
            try:
                qs = qs.filter(programa_id=int(programa_id))
            except ValueError:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'programa_id': 'Deve ser um número inteiro.'})

        return qs
