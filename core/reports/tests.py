"""
Testes do serviço de relatórios via LLM (reports.llm_service).

Cobertura:
  - extrair_dados_do_banco: agregações sobre coletas/saldos no período.
  - gerar_relatorio_narrativo: monta o prompt correto (modelo, cache_control,
    dados em JSON) usando o cliente Anthropic MOCKADO — sem custo e sem API key.
  - comportamento sem ANTHROPIC_API_KEY configurada.

Rodar:
    python manage.py test reports
"""
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Usuario
from program.models import Imovel, Programa, SaldoPontos
from collection.models import RegistroColeta
from reports.llm_service import LLMReportService


def _criar_imovel(inscricao, bairro, titular):
    return Imovel.objects.create(
        inscricao=inscricao,
        titular=titular,
        cep="60000-000",
        logradouro="Rua das Flores",
        numero="100",
        bairro=bairro,
        cidade="Fortaleza",
        estado="CE",
    )


@override_settings(ANTHROPIC_API_KEY="test-key")
class ExtrairDadosDoBancoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 'fim' com folga p/ frente: SaldoPontos.atualizado é auto_now (gravado
        # em now() ao salvar, logo após este ponto) e precisa cair na janela.
        cls.fim = timezone.now() + timedelta(minutes=5)
        cls.inicio = cls.fim - timedelta(days=30)
        dentro = timezone.now() - timedelta(days=1)

        morador = Usuario.objects.create_user(
            email="morador@example.com", password="x", nome="Morador", perfil="morador",
        )
        cls.programa = Programa.objects.create(
            nome="Coleta Premiada 2026",
            data_inicio=cls.inicio.date(),
            data_fim=cls.fim.date(),
        )

        imovel_centro = _criar_imovel("INSC-1", "Centro", morador)
        imovel_beira = _criar_imovel("INSC-2", "Beira-Mar", morador)

        # Coletas DENTRO da janela: Centro = 10+5 = 15 kg; Beira-Mar = 20 kg.
        RegistroColeta.objects.create(
            id_microservico="m1", imovel=imovel_centro, peso_kg=Decimal("10.000"),
            pontuacao=Decimal("15.00"), data_hora_coleta=dentro,
        )
        RegistroColeta.objects.create(
            id_microservico="m2", imovel=imovel_centro, peso_kg=Decimal("5.000"),
            pontuacao=Decimal("7.50"), data_hora_coleta=dentro,
        )
        RegistroColeta.objects.create(
            id_microservico="m3", imovel=imovel_beira, peso_kg=Decimal("20.000"),
            pontuacao=Decimal("30.00"), data_hora_coleta=dentro,
        )
        # Coleta FORA da janela — não deve entrar nas métricas.
        RegistroColeta.objects.create(
            id_microservico="m4", imovel=imovel_centro, peso_kg=Decimal("999.000"),
            pontuacao=Decimal("999.00"), data_hora_coleta=cls.fim - timedelta(days=400),
        )

        # SaldoPontos: 'atualizado' é auto_now => grava now() (dentro da janela).
        SaldoPontos.objects.create(
            imovel=imovel_centro, programa=cls.programa, ciclo="06-2026",
            desconto_percentual=Decimal("12.50"),
        )
        SaldoPontos.objects.create(
            imovel=imovel_beira, programa=cls.programa, ciclo="06-2026",
            desconto_percentual=Decimal("7.50"),
        )

    def test_metricas_gerais(self):
        dados = LLMReportService().extrair_dados_do_banco(self.inicio, self.fim)
        m = dados["metricas_gerais"]
        self.assertAlmostEqual(m["total_peso_kg"], 35.0)
        self.assertAlmostEqual(m["total_pontos_gerados"], 52.5)
        self.assertEqual(m["quantidade_coletas"], 3)
        self.assertEqual(m["imoveis_unicos_participantes"], 2)

    def test_top_bairros_ordenado_por_peso(self):
        dados = LLMReportService().extrair_dados_do_banco(self.inicio, self.fim)
        bairros = dados["top_bairros"]
        self.assertEqual(bairros[0]["bairro"], "Beira-Mar")
        self.assertAlmostEqual(bairros[0]["peso_kg"], 20.0)
        self.assertEqual(bairros[1]["bairro"], "Centro")
        self.assertAlmostEqual(bairros[1]["peso_kg"], 15.0)

    def test_media_desconto_iptu(self):
        dados = LLMReportService().extrair_dados_do_banco(self.inicio, self.fim)
        self.assertAlmostEqual(dados["descontos_iptu"]["media_percentual_desconto"], 10.0)

    def test_periodo_vazio_retorna_zeros(self):
        fim = self.fim - timedelta(days=365)
        inicio = fim - timedelta(days=30)
        dados = LLMReportService().extrair_dados_do_banco(inicio, fim)
        m = dados["metricas_gerais"]
        self.assertEqual(m["total_peso_kg"], 0.0)
        self.assertEqual(m["total_pontos_gerados"], 0.0)
        self.assertEqual(m["quantidade_coletas"], 0)
        self.assertEqual(m["imoveis_unicos_participantes"], 0)
        self.assertEqual(dados["top_bairros"], [])
        self.assertEqual(dados["descontos_iptu"]["media_percentual_desconto"], 0.0)


@override_settings(ANTHROPIC_API_KEY="test-key")
class GerarRelatorioNarrativoTests(TestCase):
    @patch("reports.llm_service.anthropic.Anthropic")
    def test_monta_prompt_modelo_e_cache_control(self, mock_anthropic_cls):
        mock_client = mock_anthropic_cls.return_value
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Relatório narrativo gerado.")]
        mock_client.messages.create.return_value = mock_resp

        fim = timezone.now()
        inicio = fim - timedelta(days=30)
        texto = LLMReportService().gerar_relatorio_narrativo(
            "Relatório de Impacto Mensal", inicio, fim,
        )

        self.assertEqual(texto, "Relatório narrativo gerado.")
        self.assertEqual(mock_client.messages.create.call_count, 1)

        kwargs = mock_client.messages.create.call_args.kwargs
        # Modelo exigido pela task.
        self.assertEqual(kwargs["model"], "claude-sonnet-4-6")
        # cache_control no system prompt (prompt caching).
        self.assertEqual(kwargs["system"][0]["cache_control"], {"type": "ephemeral"})
        # Dados em JSON dentro do prompt do usuário.
        user_content = kwargs["messages"][0]["content"]
        self.assertIn("metricas_gerais", user_content)
        self.assertIn("Relatório de Impacto Mensal", user_content)
        # JSON válido embutido no prompt.
        self.assertIn(json.dumps({"inicio": inicio.isoformat()})[1:-1], user_content)

    @override_settings(ANTHROPIC_API_KEY=None)
    def test_sem_api_key_retorna_erro_sem_chamar_api(self):
        service = LLMReportService()
        self.assertIsNone(service.client)
        fim = timezone.now()
        texto = service.gerar_relatorio_narrativo("X", fim - timedelta(days=30), fim)
        self.assertIn("API Key", texto)
