import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reports.local_llm_service import LocalLLMReportService


class Command(BaseCommand):
    help = 'Testa extração de dados e integração com LLM local (LM Studio)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias', type=int, default=30,
            help='Período de análise em dias (padrão: 30)',
        )
        parser.add_argument(
            '--tipo', default='Relatório de Impacto Mensal',
            help='Tipo de relatório a ser gerado',
        )

    def handle(self, *args, **options):
        service = LocalLLMReportService()
        fim = timezone.now()
        inicio = fim - timedelta(days=options['dias'])

        self.stdout.write(
            f"LLM local: {service.model}  |  endpoint: {service.endpoint}"
        )
        self.stdout.write(
            f"Período: {inicio.date()} → {fim.date()}"
        )
        self.stdout.write("─" * 60)

        self.stdout.write("\n[1/2] Extraindo dados do banco...")
        try:
            dados = service.extrair_dados_do_banco(inicio, fim)
            self.stdout.write(json.dumps(dados, indent=2, ensure_ascii=False))
            self.stdout.write(self.style.SUCCESS("✓ Extração concluída"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Erro na extração: {e}"))
            return

        self.stdout.write(f"\n[2/2] Gerando relatório via LLM local...")
        resultado = service.gerar_relatorio_narrativo(options['tipo'], inicio, fim)

        if not resultado['sucesso']:
            self.stdout.write(self.style.ERROR(resultado['relatorio']))
        else:
            self.stdout.write(self.style.SUCCESS("✓ Relatório gerado:\n"))
            self.stdout.write(resultado['relatorio'])
            self.stdout.write(f"\nTokens utilizados: {resultado['tokens_utilizados']}")
