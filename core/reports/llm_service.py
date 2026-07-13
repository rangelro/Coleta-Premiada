import json
import logging
import urllib.request
import urllib.error
from django.db.models import Sum, Count, Avg
from django.conf import settings

from collection.models import RegistroColeta
from program.models import SaldoPontos

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


class LLMReportService:
    """
    Serviço de relatórios narrativos usando a API do DeepSeek.
    """

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.endpoint = DEEPSEEK_API_URL
        self.model = DEEPSEEK_MODEL

    def extrair_dados_do_banco(self, data_inicio, data_fim, programa_id=None):
        coletas_qs = RegistroColeta.objects.filter(
            data_hora_coleta__range=(data_inicio, data_fim)
        )
        if programa_id:
            coletas_qs = coletas_qs.filter(programa_id=programa_id)

        metrics = coletas_qs.aggregate(
            total_peso=Sum('peso_kg'),
            total_pontos=Sum('pontuacao'),
            total_coletas=Count('id'),
            total_imoveis_participantes=Count('imovel', distinct=True),
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
        )

        return {
            "periodo": {
                "inicio": data_inicio.isoformat(),
                "fim": data_fim.isoformat(),
            },
            "metricas_gerais": {
                "total_peso_kg": float(metrics['total_peso'] or 0),
                "total_pontos_gerados": float(metrics['total_pontos'] or 0),
                "quantidade_coletas": metrics['total_coletas'],
                "imoveis_unicos_participantes": metrics['total_imoveis_participantes'],
            },
            "top_bairros": [
                {"bairro": b['imovel__bairro'], "peso_kg": float(b['peso'])}
                for b in top_bairros
            ],
            "descontos_iptu": {
                "media_percentual_desconto": float(descontos_metrics['media_desconto'] or 0),
            },
        }

    def _chamar_llm(self, system_prompt: str, user_prompt: str) -> tuple:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 2048,
            "temperature": 0.7,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        total_tokens = usage.get("total_tokens") or 0
        logger.info(
            "DeepSeek API usage | prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            total_tokens,
        )
        return text, total_tokens

    def gerar_relatorio_narrativo(
        self, tipo_relatorio: str, data_inicio, data_fim, programa_id=None
    ) -> dict:
        dados = self.extrair_dados_do_banco(data_inicio, data_fim, programa_id=programa_id)

        system_prompt = (
            "Você é um consultor analítico do programa 'Coleta Premiada'. "
            "Sua missão é transformar dados técnicos de reciclagem em relatórios narrativos "
            "inspiradores e informativos. Use um tom profissional, mas encorajador. "
            "Sempre formate o relatório em Markdown, usando títulos, listas e negrito para "
            "destacar pontos chave. Analise tendências, destaque o impacto ambiental "
            "(conversão de lixo em benefício) e o impacto social (desconto no IPTU)."
        )

        user_prompt = (
            f"Por favor, gere um relatório do tipo: '{tipo_relatorio}'.\n\n"
            f"Dados estatísticos coletados:\n{json.dumps(dados, indent=2, ensure_ascii=False)}\n\n"
            "Escreva uma análise profunda, não apenas repita os números. "
            "Sugira melhorias se os números estiverem baixos ou parabenize se estiverem altos."
        )

        try:
            texto, tokens = self._chamar_llm(system_prompt, user_prompt)
            return {"relatorio": texto, "tokens_utilizados": tokens, "sucesso": True}
        except urllib.error.URLError as e:
            logger.error("DeepSeek API inacessível em %s: %s", self.endpoint, e)
            return {
                "relatorio": f"Erro: não foi possível conectar à API do DeepSeek. Detalhes: {e}",
                "tokens_utilizados": 0,
                "sucesso": False,
            }
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error("Resposta inesperada da API DeepSeek: %s", e)
            return {"relatorio": f"Erro: resposta inesperada da API — {e}", "tokens_utilizados": 0, "sucesso": False}
        except Exception as e:
            logger.error("Erro ao chamar DeepSeek API: %s", e)
            return {"relatorio": f"Erro ao gerar relatório: {e}", "tokens_utilizados": 0, "sucesso": False}
