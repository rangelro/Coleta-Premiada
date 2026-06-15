import json
import logging
from django.db.models import Sum, Count, Avg
from django.conf import settings
from django.utils import timezone
import anthropic

from collection.models import RegistroColeta
from program.models import Imovel, SaldoPontos

logger = logging.getLogger(__name__)

class LLMReportService:
    """
    Serviço de integração com LLM (Anthropic) para geração de relatórios narrativos.
    """

    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY não configurada no settings.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def extrair_dados_do_banco(self, data_inicio, data_fim):
        """
        Consulta e agrega dados relevantes do banco para o período informado.
        """
        # Filtro base para o período
        coletas_qs = RegistroColeta.objects.filter(
            data_hora_coleta__range=(data_inicio, data_fim)
        )

        # Agregações gerais
        metrics = coletas_qs.aggregate(
            total_peso=Sum('peso_kg'),
            total_pontos=Sum('pontuacao'),
            total_coletas=Count('id'),
            total_imoveis_participantes=Count('imovel', distinct=True)
        )

        # Top 5 bairros mais engajados (por peso)
        top_bairros = (
            coletas_qs.values('imovel__bairro')
            .annotate(peso=Sum('peso_kg'))
            .order_by('-peso')[:5]
        )

        # Resumo de descontos no período (SaldoPontos)
        # Nota: SaldoPontos é por ciclo (MM-YYYY). Vamos pegar os do período aproximado.
        saldos_qs = SaldoPontos.objects.filter(atualizado__range=(data_inicio, data_fim))
        descontos_metrics = saldos_qs.aggregate(
            media_desconto=Avg('desconto_percentual'),
            max_desconto=Sum('desconto_percentual') # Somatório de % não faz muito sentido sem contexto, mas serve de métrica
        )

        return {
            "periodo": {
                "inicio": data_inicio.isoformat(),
                "fim": data_fim.isoformat()
            },
            "metricas_gerais": {
                "total_peso_kg": float(metrics['total_peso'] or 0),
                "total_pontos_gerados": float(metrics['total_pontos'] or 0),
                "quantidade_coletas": metrics['total_coletas'],
                "imoveis_unicos_participantes": metrics['total_imoveis_participantes']
            },
            "top_bairros": [
                {"bairro": b['imovel__bairro'], "peso_kg": float(b['peso'])}
                for b in top_bairros
            ],
            "descontos_iptu": {
                "media_percentual_desconto": float(descontos_metrics['media_desconto'] or 0)
            }
        }

    def gerar_relatorio_narrativo(self, tipo_relatorio: str, data_inicio, data_fim) -> str:
        """
        Monta o prompt, envia ao LLM e retorna o relatório em texto narrativo.
        Utiliza Prompt Caching para reduzir custos.
        """
        if not self.client:
            return "Erro: API Key da Anthropic não configurada."

        # 1. Extrai dados do banco
        dados = self.extrair_dados_do_banco(data_inicio, data_fim)

        # 2. Define a mensagem de sistema com Cache Control
        # Instruções detalhadas para garantir um bom tom e formatação.
        system_content = [
            {
                "type": "text",
                "text": (
                    "Você é um consultor analítico do programa 'Coleta Premiada'. "
                    "Sua missão é transformar dados técnicos de reciclagem em relatórios narrativos inspiradores e informativos. "
                    "Use um tom profissional, mas encorajador. "
                    "Sempre formate o relatório em Markdown, usando títulos, listas e negrito para destacar pontos chave. "
                    "Analise tendências, destaque o impacto ambiental (conversão de lixo em benefício) e o impacto social (desconto no IPTU)."
                ),
                "cache_control": {"type": "ephemeral"} # Tag de cache para economizar tokens
            }
        ]

        # 3. Define o prompt do usuário com os dados
        user_prompt = (
            f"Por favor, gere um relatório do tipo: '{tipo_relatorio}'.\n\n"
            f"Dados estatísticos coletados:\n{json.dumps(dados, indent=2)}\n\n"
            "Escreva uma análise profunda, não apenas repita os números. "
            "Sugira melhorias se os números estiverem baixos ou parabenize se estiverem altos."
        )

        try:
            # 4. Chamada à API (Claude 3.5 Haiku)
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2048,
                system=system_content,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            return response.content[0].text
        except Exception as e:
            logger.error(f"Erro ao chamar API Anthropic: {e}")
            return f"Erro ao gerar relatório: {str(e)}"
