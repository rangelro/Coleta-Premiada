from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import json
from reports.llm_service import LLMReportService

class Command(BaseCommand):
    help = 'Testa a extração de dados e a integração com LLM para relatórios'

    def handle(self, *args, **options):
        service = LLMReportService()
        
        # Define um período de teste (últimos 30 dias)
        fim = timezone.now()
        inicio = fim - timedelta(days=30)
        
        self.stdout.write(f"--- Testando extração de dados ({inicio.date()} até {fim.date()}) ---")
        
        try:
            dados = service.extrair_dados_do_banco(inicio, fim)
            self.stdout.write(json.dumps(dados, indent=2, ensure_ascii=False))
            self.stdout.write(self.style.SUCCESS("✓ Extração de dados concluída com sucesso!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Erro na extração: {e}"))
            return

        self.stdout.write("\n--- Testando chamada ao LLM (DeepSeek) ---")
        if not service.api_key:
            self.stdout.write(self.style.WARNING("! Pulando chamada à API: DEEPSEEK_API_KEY não configurada."))
        else:
            resultado = service.gerar_relatorio_narrativo("Relatório de Impacto Mensal", inicio, fim)
            self.stdout.write("\nResultado do LLM:\n")
            self.stdout.write(resultado['relatorio'])
            self.stdout.write(f"\nTokens utilizados: {resultado['tokens_utilizados']}")
 