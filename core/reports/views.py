import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsGestor
from config.pagination import StandardResultsSetPagination

from .models import RelatorioLLM
from .serializers import RelatorioLLMRequestSerializer, RelatorioLLMSerializer


def _get_llm_service():
    if getattr(settings, 'DEEPSEEK_API_KEY', None):
        print(5)

        from .llm_service import LLMReportService
        return LLMReportService()
    from .local_llm_service import LocalLLMReportService
    return LocalLLMReportService()


def _as_aware_datetime(d: datetime.date, end_of_day: bool = False) -> datetime.datetime:
    t = datetime.time.max if end_of_day else datetime.time.min
    return timezone.make_aware(datetime.datetime.combine(d, t))


class GenerateReportView(APIView):
    """
    POST /api/reports/generate

    Aciona o LLM para gerar um relatório narrativo e persiste o resultado.
    Apenas gestores podem acessar.
    """
    permission_classes = [IsGestor]

    def post(self, request):
        print(1)
        serializer = RelatorioLLMRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print(2)

        tipo = serializer.validated_data['tipo']
        periodo = serializer.validated_data['periodo']
        programa_id = serializer.validated_data.get('programa_id')
        print(3)

        inicio = _as_aware_datetime(periodo['inicio'])
        fim = _as_aware_datetime(periodo['fim'], end_of_day=True)
        print(4)

        service = _get_llm_service()
        print(6)
        resultado = service.gerar_relatorio_narrativo(tipo, inicio, fim, programa_id=programa_id)
        print(7)

        if not resultado['sucesso']:
            return Response({'detail': resultado['relatorio']}, status=status.HTTP_502_BAD_GATEWAY)

        relatorio = RelatorioLLM.objects.create(
            tipo=tipo,
            periodo_inicio=periodo['inicio'],
            periodo_fim=periodo['fim'],
            programa_id=programa_id,
            relatorio=resultado['relatorio'],
            tokens_utilizados=resultado['tokens_utilizados'],
            gerado_por=request.user,
        )

        return Response(RelatorioLLMSerializer(relatorio).data, status=status.HTTP_201_CREATED)


class ReportHistoryView(generics.ListAPIView):
    """
    GET /api/reports/history

    Lista todos os relatórios gerados (paginado).
    Apenas gestores podem acessar.
    """
    permission_classes = [IsGestor]
    serializer_class = RelatorioLLMSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = RelatorioLLM.objects.select_related('programa', 'gerado_por').order_by('-gerado_em')

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
