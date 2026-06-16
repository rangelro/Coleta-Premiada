"""
Testes do app `reports`.

Cobertura:
  - LLMReportService.extrair_dados_do_banco
  - LLMReportService.gerar_relatorio_narrativo (retorna dict com sucesso/tokens)
  - POST /api/reports/generate
  - GET  /api/reports/history

Rodar:
    python manage.py test reports
"""
import datetime
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Usuario
from collection.models import RegistroColeta
from program.models import Imovel, Programa, SaldoPontos
from reports.llm_service import LLMReportService
from reports.models import RelatorioLLM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


# ---------------------------------------------------------------------------
# LLMReportService.extrair_dados_do_banco
# ---------------------------------------------------------------------------

@override_settings(DEEPSEEK_API_KEY="test-key")
class ExtrairDadosDoBancoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
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
        RegistroColeta.objects.create(
            id_microservico="m4", imovel=imovel_centro, peso_kg=Decimal("999.000"),
            pontuacao=Decimal("999.00"), data_hora_coleta=cls.fim - timedelta(days=400),
        )

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


# ---------------------------------------------------------------------------
# LLMReportService.gerar_relatorio_narrativo — retorna dict
# ---------------------------------------------------------------------------

@override_settings(DEEPSEEK_API_KEY="test-key")
class GerarRelatorioNarrativoTests(TestCase):
    @patch("reports.llm_service.openai.OpenAI")
    def test_retorna_dict_com_relatorio_e_tokens(self, mock_openai_cls):
        mock_client = mock_openai_cls.return_value
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="Relatório narrativo gerado."))]
        mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_client.chat.completions.create.return_value = mock_resp

        fim = timezone.now()
        inicio = fim - timedelta(days=30)
        resultado = LLMReportService().gerar_relatorio_narrativo(
            "Relatório de Impacto Mensal", inicio, fim,
        )

        self.assertTrue(resultado['sucesso'])
        self.assertEqual(resultado['relatorio'], "Relatório narrativo gerado.")
        self.assertEqual(resultado['tokens_utilizados'], 30)

    @patch("reports.llm_service.openai.OpenAI")
    def test_monta_prompt_correto(self, mock_openai_cls):
        mock_client = mock_openai_cls.return_value
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_resp.usage = MagicMock(prompt_tokens=5, completion_tokens=5, total_tokens=10)
        mock_client.chat.completions.create.return_value = mock_resp

        fim = timezone.now()
        inicio = fim - timedelta(days=30)
        LLMReportService().gerar_relatorio_narrativo("Relatório de Impacto Mensal", inicio, fim)

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "deepseek-chat")
        self.assertEqual(kwargs["messages"][0]["role"], "system")
        user_content = kwargs["messages"][1]["content"]
        self.assertIn("metricas_gerais", user_content)
        self.assertIn("Relatório de Impacto Mensal", user_content)
        self.assertIn(json.dumps({"inicio": inicio.isoformat()})[1:-1], user_content)

    @override_settings(DEEPSEEK_API_KEY=None)
    def test_sem_api_key_retorna_sucesso_false(self):
        service = LLMReportService()
        self.assertIsNone(service.client)
        fim = timezone.now()
        resultado = service.gerar_relatorio_narrativo("X", fim - timedelta(days=30), fim)
        self.assertFalse(resultado['sucesso'])
        self.assertIn("API Key", resultado['relatorio'])
        self.assertEqual(resultado['tokens_utilizados'], 0)


# ---------------------------------------------------------------------------
# POST /api/reports/generate
# ---------------------------------------------------------------------------

@override_settings(DEEPSEEK_API_KEY="test-key")
class GenerateReportViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = Usuario.objects.create_user(
            email="gestor@example.com", password="x", nome="Gestor", perfil="gestor",
        )
        cls.morador = Usuario.objects.create_user(
            email="morador2@example.com", password="x", nome="Morador", perfil="morador",
        )
        cls.programa = Programa.objects.create(
            nome="Prog 2026",
            data_inicio=datetime.date(2026, 1, 1),
            data_fim=datetime.date(2026, 12, 31),
        )

    def _post(self, data, user=None):
        token = _token(user or self.gestor)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return self.client.post('/api/reports/generate', data, format='json')

    @patch("reports.views._get_llm_service")
    def test_gestor_gera_relatorio_e_salva(self, mock_get_service):
        mock_svc = MagicMock()
        mock_svc.gerar_relatorio_narrativo.return_value = {
            "relatorio": "Relatório de participação gerado.",
            "tokens_utilizados": 150,
            "sucesso": True,
        }
        mock_get_service.return_value = mock_svc

        resp = self._post({
            "tipo": "participacao",
            "periodo": {"inicio": "2026-01-01", "fim": "2026-06-30"},
        })

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['tipo'], 'participacao')
        self.assertEqual(resp.data['relatorio'], "Relatório de participação gerado.")
        self.assertEqual(resp.data['tokens_utilizados'], 150)
        self.assertEqual(resp.data['periodo'], {'inicio': '2026-01-01', 'fim': '2026-06-30'})
        self.assertEqual(RelatorioLLM.objects.count(), 1)

    @patch("reports.views._get_llm_service")
    def test_com_programa_id_opcional(self, mock_get_service):
        mock_svc = MagicMock()
        mock_svc.gerar_relatorio_narrativo.return_value = {
            "relatorio": "Relatório de impacto.", "tokens_utilizados": 80, "sucesso": True,
        }
        mock_get_service.return_value = mock_svc

        resp = self._post({
            "tipo": "impacto",
            "periodo": {"inicio": "2026-01-01", "fim": "2026-06-30"},
            "programa_id": self.programa.pk,
        })

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        relatorio = RelatorioLLM.objects.get()
        self.assertEqual(relatorio.programa_id, self.programa.pk)
        _, kwargs = mock_svc.gerar_relatorio_narrativo.call_args
        self.assertEqual(kwargs['programa_id'], self.programa.pk)

    def test_morador_nao_pode_gerar(self):
        resp = self._post(
            {"tipo": "ranking", "periodo": {"inicio": "2026-01-01", "fim": "2026-06-30"}},
            user=self.morador,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_tipo_invalido_retorna_400(self):
        resp = self._post({"tipo": "invalido", "periodo": {"inicio": "2026-01-01", "fim": "2026-06-30"}})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_periodo_invertido_retorna_400(self):
        resp = self._post({"tipo": "impacto", "periodo": {"inicio": "2026-06-30", "fim": "2026-01-01"}})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("reports.views._get_llm_service")
    def test_falha_no_llm_retorna_502_sem_salvar(self, mock_get_service):
        mock_svc = MagicMock()
        mock_svc.gerar_relatorio_narrativo.return_value = {
            "relatorio": "Erro: LM Studio não está respondendo.",
            "tokens_utilizados": 0,
            "sucesso": False,
        }
        mock_get_service.return_value = mock_svc

        resp = self._post({"tipo": "auditoria", "periodo": {"inicio": "2026-01-01", "fim": "2026-06-30"}})

        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(RelatorioLLM.objects.count(), 0)

    def test_sem_autenticacao_retorna_401(self):
        resp = self.client.post('/api/reports/generate', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# GET /api/reports/history
# ---------------------------------------------------------------------------

class ReportHistoryViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = Usuario.objects.create_user(
            email="gestor2@example.com", password="x", nome="Gestor2", perfil="gestor",
        )
        cls.supervisor = Usuario.objects.create_user(
            email="supervisor@example.com", password="x", nome="Supervisor", perfil="supervisor",
        )
        cls.programa = Programa.objects.create(
            nome="Prog 2026 H",
            data_inicio=datetime.date(2026, 1, 1),
            data_fim=datetime.date(2026, 12, 31),
        )
        RelatorioLLM.objects.create(
            tipo='participacao',
            periodo_inicio='2026-01-01',
            periodo_fim='2026-06-30',
            relatorio='Texto A',
            tokens_utilizados=100,
            gerado_por=cls.gestor,
        )
        RelatorioLLM.objects.create(
            tipo='ranking',
            periodo_inicio='2026-01-01',
            periodo_fim='2026-06-30',
            programa=cls.programa,
            relatorio='Texto B',
            tokens_utilizados=200,
            gerado_por=cls.gestor,
        )

    def _get(self, params='', user=None):
        token = _token(user or self.gestor)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return self.client.get(f'/api/reports/history{params}')

    def test_gestor_lista_todos(self):
        resp = self._get()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 2)

    def test_filtro_por_tipo(self):
        resp = self._get('?tipo=ranking')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['tipo'], 'ranking')

    def test_filtro_por_programa_id(self):
        resp = self._get(f'?programa_id={self.programa.pk}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)

    def test_supervisor_nao_pode_listar(self):
        resp = self._get(user=self.supervisor)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sem_autenticacao_retorna_401(self):
        resp = self.client.get('/api/reports/history')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_campos_obrigatorios_na_resposta(self):
        resp = self._get()
        item = resp.data['results'][0]
        for campo in ('id', 'tipo', 'periodo', 'relatorio', 'tokens_utilizados', 'gerado_em'):
            self.assertIn(campo, item)
        self.assertIn('inicio', item['periodo'])
        self.assertIn('fim', item['periodo'])