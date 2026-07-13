import logging

from celery import shared_task
from django.utils import timezone

from .models import RelatorioLLM

logger = logging.getLogger(__name__)


def _get_llm_service():
    from django.conf import settings
    if getattr(settings, 'DEEPSEEK_API_KEY', None):
        from .llm_service import LLMReportService
        return LLMReportService()
    from .local_llm_service import LocalLLMReportService
    return LocalLLMReportService()


def _as_aware_datetime(d, end_of_day=False):
    import datetime
    t = datetime.time.max if end_of_day else datetime.time.min
    return timezone.make_aware(datetime.datetime.combine(d, t))


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def gerar_relatorio_async(self, report_id: int):
    """
    Tarefa Celery que gera o relatório via LLM de forma assíncrona.
    Atualiza o status e conteúdo do RelatorioLLM conforme progride.
    """
    try:
        relatorio = RelatorioLLM.objects.get(pk=report_id)
    except RelatorioLLM.DoesNotExist:
        logger.error("RelatorioLLM id=%s não encontrado.", report_id)
        return

    relatorio.status = 'processando'
    relatorio.save(update_fields=['status'])

    service = _get_llm_service()
    inicio = _as_aware_datetime(relatorio.periodo_inicio)
    fim = _as_aware_datetime(relatorio.periodo_fim, end_of_day=True)

    try:
        resultado = service.gerar_relatorio_narrativo(
            relatorio.tipo, inicio, fim, programa_id=relatorio.programa_id,
        )

        if resultado['sucesso']:
            texto = resultado['relatorio']
            if relatorio.direcionamento:
                texto = (
                    f"**Direcionamento solicitado:** {relatorio.direcionamento}\n\n"
                    f"---\n\n"
                    f"{texto}"
                )
            relatorio.relatorio = texto
            relatorio.tokens_utilizados = resultado['tokens_utilizados']
            relatorio.status = 'concluido'
        else:
            relatorio.relatorio = resultado['relatorio']
            relatorio.status = 'erro'

        relatorio.save(update_fields=['relatorio', 'tokens_utilizados', 'status'])
        logger.info("Relatório id=%s concluído com status=%s.", report_id, relatorio.status)

    except Exception as e:
        logger.error("Erro ao gerar relatório id=%s: %s", report_id, e)
        relatorio.relatorio = f"Erro ao gerar relatório: {e}"
        relatorio.status = 'erro'
        relatorio.save(update_fields=['relatorio', 'status'])
