"""
Class-Based Views do app `program`.

Cobre:
- /properties/*      CRUD de imóveis (e gerenciamento de moradores vinculados)
- /programs/*        CRUD de programas
- /programs/:id/rules       regras configuráveis do programa
- /consolidations/*  execução e consulta de consolidações de ciclo
- /benefits/*        benefícios finais por imóvel
- /reports/*         relatórios agregados
"""
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsGestor, IsGestorOrSupervisor, ReadOnlyOrGestor
from accounts.models import Usuario

from .models import (
    Programa, RegraPrograma,
    Imovel, SaldoPontos, Consolidacao,
)
from .serializers import (
    ProgramaSerializer, RegraProgramaSerializer,
    ImovelSerializer, SaldoPontosSerializer, ConsolidacaoSerializer,
)
from .business_rules import aplicar_teto, DESCONTO_MAXIMO


# ---------------------------------------------------------------------------
# IMÓVEIS  /properties/*
# ---------------------------------------------------------------------------
class ImovelListCreateView(generics.ListCreateAPIView):
    """
    🔒 GET  /properties — lista imóveis (filtra pelo titular caso seja morador).
    🔒 POST /properties — cria imóvel e publica adesão na fila.
    """
    serializer_class = ImovelSerializer

    def get_queryset(self):
        qs = Imovel.objects.select_related('titular').all()
        user = self.request.user
        # Regra de negócio: morador só enxerga seus próprios imóveis.
        if getattr(user, 'perfil', None) == 'morador':
            qs = qs.filter(Q(titular=user) | Q(moradores=user)).distinct()
        return qs

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()


class ImovelDetailView(generics.RetrieveUpdateAPIView):
    """
    🔒 GET   /properties/:id — busca um imóvel.
    🔒 PATCH /properties/:id — atualiza um imóvel (gestor/supervisor).
    """
    serializer_class = ImovelSerializer
    queryset = Imovel.objects.all()

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsGestorOrSupervisor()]
        return [IsAuthenticated()]


class ImovelAddUserView(APIView):
    """🔒 POST /properties/:id/users — vincula um morador a um imóvel."""
    permission_classes = [IsGestorOrSupervisor]

    def post(self, request, id):
        imovel = get_object_or_404(Imovel, pk=id)
        user_id = request.data.get('user_id') or request.data.get('userId')
        if not user_id:
            return Response({'detail': 'user_id obrigatório.'}, status=400)

        usuario = get_object_or_404(Usuario, pk=user_id)
        if usuario.perfil != 'morador':
            return Response(
                {'detail': 'Apenas usuários com perfil "morador" podem ser vinculados.'},
                status=400,
            )

        imovel.moradores.add(usuario)
        return Response(ImovelSerializer(imovel).data, status=status.HTTP_200_OK)


class ImovelRemoveUserView(APIView):
    """🔒 DELETE /properties/:id/users/:userId — remove um morador do imóvel."""
    permission_classes = [IsGestorOrSupervisor]

    def delete(self, request, id, userId):
        imovel = get_object_or_404(Imovel, pk=id)

        if imovel.titular_id == int(userId):
            return Response(
                {'detail': 'Não é permitido remover o titular do imóvel.'},
                status=400,
            )

        usuario = get_object_or_404(Usuario, pk=userId)
        imovel.moradores.remove(usuario)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# PROGRAMAS  /programs/*
# ---------------------------------------------------------------------------
class ProgramaListCreateView(generics.ListCreateAPIView):
    """
    🔒 GET  /programs — lista programas (qualquer autenticado).
    🔒 POST /programs — cria programa (somente gestor).
    """
    serializer_class = ProgramaSerializer
    queryset = Programa.objects.all().prefetch_related('regras')
    permission_classes = [ReadOnlyOrGestor]


class ProgramaDetailView(generics.RetrieveUpdateAPIView):
    """
    🔒 GET   /programs/:id — detalha um programa.
    🔒 PATCH /programs/:id — atualiza um programa (gestor).
    """
    serializer_class = ProgramaSerializer
    queryset = Programa.objects.all().prefetch_related('regras')
    permission_classes = [ReadOnlyOrGestor]



class ProgramaRulesView(APIView):
    """
    🔒 GET   /programs/:id/rules — retorna regras do programa.
    🔒 PATCH /programs/:id/rules — atualiza regras do programa (gestor).
    """
    permission_classes = [ReadOnlyOrGestor]

    def get(self, request, id):
        programa = get_object_or_404(Programa, pk=id)
        regras, _ = RegraPrograma.objects.get_or_create(programa=programa)
        return Response(RegraProgramaSerializer(regras).data)

    def patch(self, request, id):
        programa = get_object_or_404(Programa, pk=id)
        regras, _ = RegraPrograma.objects.get_or_create(programa=programa)
        serializer = RegraProgramaSerializer(regras, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# CONSOLIDAÇÕES  /consolidations/*
# ---------------------------------------------------------------------------
class ConsolidacaoRunView(APIView):
    """
    🔒 POST /consolidations/run — dispara consolidação do programa.

    Regras de negócio aplicadas:
    - Apenas gestor pode executar.
    - Soma a pontuação por imóvel no ciclo informado.
    - Converte pontos em desconto via `RegraPrograma.pontos_por_real`.
    - Aplica o teto `DESCONTO_MAXIMO` (40%) chamando `aplicar_teto`.
    """
    permission_classes = [IsGestor]

    def post(self, request):
        from collection.models import RegistroColeta

        programa_id = request.data.get('programa_id')
        ciclo = request.data.get('ciclo')  # ex: '12-2026'
        if not programa_id or not ciclo:
            return Response(
                {'detail': 'programa_id e ciclo são obrigatórios.'},
                status=400,
            )
        programa = get_object_or_404(Programa, pk=programa_id)
        regras, _ = RegraPrograma.objects.get_or_create(programa=programa)

        consolidacao = Consolidacao.objects.create(
            programa=programa,
            executada_por=request.user,
            status='processando',
        )

        try:
            agregados = (
                RegistroColeta.objects
                .values('imovel')
                .annotate(total=Sum('pontuacao'))
            )
            total_imoveis = 0
            total_pontos = Decimal('0')

            for linha in agregados:
                imovel_id = linha['imovel']
                pontos = Decimal(linha['total'] or 0)
                if pontos < regras.minimo_para_beneficio:
                    continue
                # Converte pontos -> % de desconto.
                novo_desconto = (pontos / regras.pontos_por_real).quantize(Decimal('0.01'))

                saldo, _ = SaldoPontos.objects.get_or_create(
                    imovel_id=imovel_id, ciclo=ciclo,
                    defaults={'desconto_percentual': Decimal('0')},
                )
                aplicavel = aplicar_teto(saldo.desconto_percentual, novo_desconto)
                saldo.desconto_percentual = (saldo.desconto_percentual + aplicavel).quantize(Decimal('0.01'))
                # Respeita o teto do PROGRAMA (caso seja diferente do default).
                teto_programa = programa.desconto_maximo
                if saldo.desconto_percentual > teto_programa:
                    saldo.desconto_percentual = teto_programa
                saldo.save()

                total_imoveis += 1
                total_pontos += pontos

            consolidacao.total_imoveis = total_imoveis
            consolidacao.total_pontos = total_pontos
            consolidacao.status = 'concluida'
            consolidacao.save()
        except Exception as e:
            consolidacao.status = 'falhou'
            consolidacao.observacao = str(e)
            consolidacao.save()
            return Response(
                {'detail': 'Falha na consolidação.', 'erro': str(e)},
                status=500,
            )

        return Response(ConsolidacaoSerializer(consolidacao).data, status=201)


class ConsolidacaoListView(generics.ListAPIView):
    """🔒 GET /consolidations — lista consolidações já executadas."""
    permission_classes = [IsGestorOrSupervisor]
    serializer_class = ConsolidacaoSerializer
    queryset = Consolidacao.objects.select_related('programa', 'executada_por')


class ConsolidacaoDetailView(generics.RetrieveAPIView):
    """🔒 GET /consolidations/:id — detalhe de uma consolidação."""
    permission_classes = [IsGestorOrSupervisor]
    serializer_class = ConsolidacaoSerializer
    queryset = Consolidacao.objects.select_related('programa', 'executada_por')


# ---------------------------------------------------------------------------
# BENEFÍCIOS  /benefits/*
# ---------------------------------------------------------------------------
class BeneficioListView(generics.ListAPIView):
    """🔒 GET /benefits — retorna todos os benefícios (saldos) consolidados."""
    permission_classes = [IsGestorOrSupervisor]
    serializer_class = SaldoPontosSerializer
    queryset = SaldoPontos.objects.select_related('imovel')


class BeneficioDetailView(APIView):
    """
    🔒 GET /benefits/:propertyId — retorna o benefício final do imóvel.

    Soma o desconto entre todos os ciclos do imóvel e aplica o teto absoluto.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, propertyId):
        imovel = get_object_or_404(Imovel, pk=propertyId)

        # Morador só pode acessar seus próprios benefícios.
        if request.user.perfil == 'morador' and imovel.titular_id != request.user.id:
            return Response({'detail': 'Sem permissão.'}, status=403)

        total = (
            SaldoPontos.objects.filter(imovel=imovel)
            .aggregate(total=Sum('desconto_percentual'))['total'] or Decimal('0')
        )
        teto = imovel.titular.imoveis.first()  # placeholder; usaremos DESCONTO_MAXIMO
        desconto_final = min(Decimal(total), DESCONTO_MAXIMO)

        return Response({
            'imovel': imovel.inscricao,
            'titular': imovel.titular.nome,
            'desconto_total_percentual': str(desconto_final),
            'saldos_por_ciclo': SaldoPontosSerializer(
                SaldoPontos.objects.filter(imovel=imovel), many=True
            ).data,
        })


# ---------------------------------------------------------------------------
# RELATÓRIOS  /reports/*
# ---------------------------------------------------------------------------
class ReportParticipationView(APIView):
    """🔒 GET /reports/participation — quem participou do programa."""
    permission_classes = [IsGestorOrSupervisor]

    def get(self, request):
        from collection.models import RegistroColeta

        participantes = (
            RegistroColeta.objects
            .values(
                'imovel__inscricao',
                'imovel__titular__nome',
            )
            .annotate(
                coletas=Count('id'),
                pontos=Sum('pontuacao'),
            )
            .order_by('-pontos')
        )
        return Response(list(participantes))



class ReportRankingView(APIView):
    """🔒 GET /reports/ranking — ranking de imóveis por pontuação."""
    permission_classes = [IsGestorOrSupervisor]

    def get(self, request):
        from collection.models import RegistroColeta

        ranking = (
            RegistroColeta.objects
            .values('imovel__inscricao', 'imovel__titular__nome')
            .annotate(pontos=Sum('pontuacao'))
            .order_by('-pontos')[:50]
        )
        return Response(list(ranking))


class ReportImpactView(APIView):
    """🔒 GET /reports/impact — impacto agregado do programa."""
    permission_classes = [IsGestorOrSupervisor]

    def get(self, request):
        from collection.models import RegistroColeta

        total_coletas = RegistroColeta.objects.count()
        total_pontos = RegistroColeta.objects.aggregate(t=Sum('pontuacao'))['t'] or 0
        total_imoveis_participantes = (
            RegistroColeta.objects.values('imovel').distinct().count()
        )
        total_desconto_concedido = (
            SaldoPontos.objects.aggregate(t=Sum('desconto_percentual'))['t'] or 0
        )

        return Response({
            'total_coletas': total_coletas,
            'total_pontos': total_pontos,
            'total_imoveis_participantes': total_imoveis_participantes,
            'soma_desconto_percentual': str(total_desconto_concedido),
        })
