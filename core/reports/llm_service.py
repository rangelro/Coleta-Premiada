import json
import logging
from django.db.models import Sum, Count, Avg
from django.conf import settings
from django.utils import timezone
import openai

from collection.models import RegistroColeta
from program.models import Imovel, SaldoPontos

logger = logging.getLogger(__name__)

class LLMReportService:
    """
    Serviço de integração com LLM (DeepSeek) para geração de relatórios narrativos.
    """

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY não configurada no settings.")
            self.client = None
        else:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com",
            )

    def extrair_dados_do_banco(self, data_inicio, data_fim, programa_id=None):
        """
        Consulta e agrega dados relevantes do banco para o período informado.
        """
        coletas_qs = RegistroColeta.objects.filter(
            data_hora_coleta__range=(data_inicio, data_fim)
        )
        if programa_id:
            coletas_qs = coletas_qs.filter(programa_id=programa_id)

        metrics = coletas_qs.aggregate(
            total_peso=Sum('peso_kg'),
            total_pontos=Sum('pontuacao'),
            total_coletas=Count('id'),
            total_imoveis_participantes=Count('imovel', distinct=True)
        )

        top_bairros = (
            coletas_qs.values('imovel__bairro')
            .annotate(peso=Sum('peso_kg'))
            .order_by('-peso')[:5]
        )

        saldos_qs = SaldoPontos.objects.filter(atualizado__range=(data_inicio, data_fim))
        if programa_id:
            saldos_qs = saldos_qs.filter(programa_id=programa_id)
        descontos_metrics = saldos_qs.aggregate(
            media_desconto=Avg('desconto_percentual'),
            max_desconto=Sum('desconto_percentual')
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

    def gerar_relatorio_narrativo(
        self, tipo_relatorio: str, data_inicio, data_fim, programa_id=None
    ) -> dict:
        """
        Monta o prompt, envia ao DeepSeek e retorna dict com relatório e uso de tokens.
        """
        if not self.client:
            return {"relatorio": "Erro: API Key do DeepSeek não configurada.", "tokens_utilizados": 0, "sucesso": False}

        dados = self.extrair_dados_do_banco(data_inicio, data_fim, programa_id=programa_id)

        system_prompt = (
            "Você é um consultor analítico do programa 'Coleta Premiada'. "
            "Sua missão é transformar dados técnicos de reciclagem em relatórios narrativos inspiradores e informativos. "
            "Use um tom profissional, mas encorajador. "
            "Sempre formate o relatório em Markdown, usando títulos, listas e negrito para destacar pontos chave. "
            "Analise tendências, destaque o impacto ambiental (conversão de lixo em benefício) e o impacto social (desconto no IPTU)."
        )

        user_prompt = (
            f"Por favor, gere um relatório do tipo: '{tipo_relatorio}'.\n\n"
            f"Dados estatísticos coletados:\n{json.dumps(dados, indent=2)}\n\n"
            "Escreva uma análise profunda, não apenas repita os números. "
            "Sugira melhorias se os números estiverem baixos ou parabenize se estiverem altos."
        )

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )

            usage = response.usage
            logger.info(
                "LLM usage | prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )

            return {
                "relatorio": response.choices[0].message.content,
                "tokens_utilizados": usage.total_tokens,
                "sucesso": True,
            }
        except Exception as e:
            logger.error(f"Erro ao chamar API DeepSeek: {e}")
            return {"relatorio": f"Erro ao gerar relatório: {str(e)}", "tokens_utilizados": 0, "sucesso": False}