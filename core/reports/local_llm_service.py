import json
import logging
import urllib.request
import urllib.error
from django.db.models import Sum, Count, Avg
from django.conf import settings

from collection.models import RegistroColeta
from program.models import SaldoPontos

logger = logging.getLogger(__name__)


class LocalLLMReportService:
    """
    Serviço de relatórios narrativos usando LLM local via LM Studio.
    Compatível com a API OpenAI (POST /v1/chat/completions).
    """

    def __init__(self):
        self.base_url = getattr(settings, 'LOCAL_LLM_BASE_URL', 'http://127.0.0.1:1234')
        self.model = getattr(settings, 'LOCAL_LLM_MODEL', 'google/gemma-4-e2b')
        self.endpoint = f"{self.base_url}/v1/chat/completions"

    def extrair_dados_do_banco(self, data_inicio, data_fim):
        """
        Consulta e agrega dados relevantes do banco para o período informado.
        Idêntico ao LLMReportService — reutilizável sem depender da API Anthropic.
        """
        coletas_qs = RegistroColeta.objects.filter(
            data_hora_coleta__range=(data_inicio, data_fim)
        )

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

    def _chamar_llm(self, system_prompt: str, user_prompt: str) -> str:
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
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        logger.info(
            "Local LLM usage | prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
        )
        return text

    def gerar_relatorio_narrativo(self, tipo_relatorio: str, data_inicio, data_fim) -> str:
        """
        Extrai dados do banco, monta o prompt e chama o LLM local via LM Studio.
        """
        dados = self.extrair_dados_do_banco(data_inicio, data_fim)

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
            return self._chamar_llm(system_prompt, user_prompt)
        except urllib.error.URLError as e:
            logger.error("LM Studio inacessível em %s: %s", self.endpoint, e)
            return f"Erro: LM Studio não está respondendo em {self.endpoint}. Verifique se o servidor está rodando."
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error("Resposta inesperada do LLM local: %s", e)
            return f"Erro: resposta inesperada do LLM local — {e}"
        except Exception as e:
            logger.error("Erro ao chamar LLM local: %s", e)
            return f"Erro ao gerar relatório: {e}"
