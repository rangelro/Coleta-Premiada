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

from django.db import transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsGestor, IsGestorOrSupervisor, IsSupervisor, ReadOnlyOrGestor
from accounts.models import Usuario
from accounts.scoping import escopar_por_cidade, usuario_pode_ver_cidade

from .models import (
    Imovel, Programa, RegraPrograma, SaldoPontos,
    Consolidacao, ConstantePontuacao, Ciclo
)
from .serializers import (
    ProgramaSerializer, RegraProgramaSerializer,
    ImovelSerializer, SaldoPontosSerializer, ConsolidacaoSerializer,
    ConstantePontuacaoSerializer, CicloSerializer
)
from .business_rules import aplicar_teto, DESCONTO_MAXIMO

from config.pagination import StandardResultsSetPagination
from rest_framework.exceptions import ValidationError


class CicloViewSet(viewsets.ModelViewSet):
    """
    CRUD para gerenciar os ciclos de um programa.
    """
    serializer_class = CicloSerializer
    permission_classes = [IsGestorOrSupervisor]

    def get_queryset(self):
        qs = Ciclo.objects.all().order_by('-data_inicio')
        programa_id = self.request.query_params.get('programa_id')
        if programa_id:
            qs = qs.filter(programa_id=programa_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

# ---------------------------------------------------------------------------
# IMÓVEIS  /properties/*
# ---------------------------------------------------------------------------
class ImovelListCreateView(generics.ListCreateAPIView):
    """
    🔒 GET  /properties — lista imóveis (filtra pelo titular caso seja morador).
    🔒 POST /properties — cria imóvel e publica adesão na fila.
    """
    serializer_class = ImovelSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Imovel.objects.select_related('titular').all().order_by('id')
        user = self.request.user
        # Regra de negócio: morador só enxerga seus próprios imóveis.
        if getattr(user, 'perfil', None) == 'morador':
            qs = qs.filter(Q(titular=user) | Q(moradores=user)).distinct()
        else:
            # Gestor/supervisor só enxergam imóveis da própria cidade;
            # gerente_geral enxerga todas.
            qs = escopar_por_cidade(qs, user, 'cidade')

        # Filtros administrativos
        bairro = self.request.query_params.get('bairro')
        if bairro:
            qs = qs.filter(bairro__icontains=bairro)
            
        cidade = self.request.query_params.get('cidade')
        if cidade:
            qs = qs.filter(cidade__icontains=cidade)
            
        ativo = self.request.query_params.get('ativo')
        if ativo is not None:
            if ativo.lower() == 'true':
                qs = qs.filter(ativo=True)
            elif ativo.lower() == 'false':
                qs = qs.filter(ativo=False)
                
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(inscricao__icontains=search) | Q(titular__nome__icontains=search)
            )

        return qs

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()


class ImovelDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /properties/:id — busca um imóvel.
    PATCH /properties/:id — atualiza um imóvel (gestor/supervisor).
    """
    serializer_class = ImovelSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsGestorOrSupervisor()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return escopar_por_cidade(Imovel.objects.all(), self.request.user, 'cidade')

    def get_object(self):
        # Suporta busca por ID primário (inteiro) ou inscrição imobiliária (string),
        # necessário para integração com o microsserviço que usa inscrição como identificador.
        queryset = self.filter_queryset(self.get_queryset())
        val = self.kwargs[self.lookup_url_kwarg or self.lookup_field or 'pk']
        try:
            obj = queryset.get(pk=val)
        except (ValueError, Imovel.DoesNotExist):
            obj = get_object_or_404(queryset, inscricao=val)
        self.check_object_permissions(self.request, obj)
        return obj


class ImovelAddUserView(APIView):
    """ POST /properties/:id/users — vincula um morador a um imóvel."""
    permission_classes = [IsGestorOrSupervisor]

    def post(self, request, id):
        qs = escopar_por_cidade(Imovel.objects.all(), request.user, 'cidade')
        try:
            imovel = qs.get(pk=id)
        except (ValueError, Imovel.DoesNotExist):
            imovel = get_object_or_404(qs, inscricao=id)
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
    """ DELETE /properties/:id/users/:userId — remove um morador do imóvel."""
    permission_classes = [IsGestorOrSupervisor]

    def delete(self, request, id, userId):
        qs = escopar_por_cidade(Imovel.objects.all(), request.user, 'cidade')
        try:
            imovel = qs.get(pk=id)
        except (ValueError, Imovel.DoesNotExist):
            imovel = get_object_or_404(qs, inscricao=id)

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
     GET  /programs — lista programas (qualquer autenticado).
     POST /programs — cria programa (somente gestor).
    """
    serializer_class = ProgramaSerializer
    queryset = Programa.objects.all().prefetch_related('regras')
    permission_classes = [ReadOnlyOrGestor]


class ProgramaDetailView(generics.RetrieveUpdateAPIView):
    """
     GET   /programs/:id — detalha um programa.
     PATCH /programs/:id — atualiza um programa (gestor).
    """
    serializer_class = ProgramaSerializer
    queryset = Programa.objects.all().prefetch_related('regras')
    permission_classes = [ReadOnlyOrGestor]



class ProgramaRulesView(APIView):
    """
     GET   /programs/:id/rules — retorna regras do programa.
     PATCH /programs/:id/rules — atualiza regras do programa (gestor).
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
    POST /program/consolidations/run
    Inicia o cálculo de benefícios para um ciclo aberto.
    Payload: { "programa_id": 1, "ciclo_id": 1 }
    """
    permission_classes = [IsGestor]

    def post(self, request):
        from collection.models import RegistroColeta

        programa_id = request.data.get('programa_id')
        ciclo_id = request.data.get('ciclo_id')

        if not programa_id or not ciclo_id:
            return Response({'detail': 'programa_id e ciclo_id são obrigatórios.'}, status=400)

        programa = get_object_or_404(Programa, pk=programa_id)
        ciclo = get_object_or_404(Ciclo, pk=ciclo_id, programa=programa)

        if ciclo.status == 'fechado':
            return Response({'detail': 'Este ciclo já está fechado e consolidado.'}, status=400)

        regras, _ = RegraPrograma.objects.get_or_create(programa=programa)

        # Criado antes do bloco atômico para persistir mesmo em caso de falha
        consolidacao = Consolidacao.objects.create(
            programa=programa,
            ciclo=ciclo,
            executada_por=request.user,
            status='processando',
        )

        try:
            with transaction.atomic():
                coletas_validas = RegistroColeta.objects.filter(
                    programa=programa,
                    data_hora_coleta__date__gte=ciclo.data_inicio,
                    data_hora_coleta__date__lte=ciclo.data_fim,
                    ciclo_consolidado__isnull=True,
                )
                agregados = coletas_validas.values('imovel').annotate(total=Sum('pontuacao'))

                total_imoveis = 0
                total_pontos = Decimal('0')

                for linha in agregados:
                    imovel_id = linha['imovel']
                    pontos = Decimal(linha['total'] or 0)
                    if pontos < regras.minimo_para_beneficio:
                        continue

                    novo_desconto = (pontos / regras.pontos_por_real).quantize(Decimal('0.01'))

                    saldo, _ = SaldoPontos.objects.get_or_create(
                        imovel_id=imovel_id, programa=programa, ciclo=ciclo,
                        defaults={'desconto_percentual': Decimal('0')},
                    )

                    aplicavel = aplicar_teto(saldo.desconto_percentual, novo_desconto)
                    saldo.desconto_percentual = (saldo.desconto_percentual + aplicavel).quantize(Decimal('0.01'))

                    teto_programa = programa.desconto_maximo
                    if saldo.desconto_percentual > teto_programa:
                        saldo.desconto_percentual = teto_programa
                    saldo.save()

                    coletas_validas.filter(imovel_id=imovel_id).update(ciclo_consolidado=ciclo)

                    total_imoveis += 1
                    total_pontos += pontos

                consolidacao.total_imoveis = total_imoveis
                consolidacao.total_pontos = total_pontos
                consolidacao.status = 'concluida'
                consolidacao.save()

                ciclo.status = 'fechado'
                ciclo.save()

        except Exception as e:
            consolidacao.status = 'falhou'
            consolidacao.observacao = str(e)
            consolidacao.save()
            return Response({'detail': 'Falha na consolidação.', 'erro': str(e)}, status=500)

        return Response(ConsolidacaoSerializer(consolidacao).data, status=201)


class ConsolidacaoListView(generics.ListAPIView):
    """ GET /consolidations — lista consolidações já executadas."""
    permission_classes = [IsGestorOrSupervisor]
    serializer_class = ConsolidacaoSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Consolidacao.objects.select_related('programa', 'executada_por', 'ciclo').all().order_by('-executada_em')
        
        programa_id = self.request.query_params.get('programa_id')
        if programa_id:
            try:
                qs = qs.filter(programa_id=int(programa_id))
            except ValueError:
                raise ValidationError({'programa_id': 'Deve ser um número inteiro.'})

        return qs


class ConsolidacaoDetailView(generics.RetrieveAPIView):
    """ GET /consolidations/:id — detalhe de uma consolidação."""
    permission_classes = [IsGestorOrSupervisor]
    serializer_class = ConsolidacaoSerializer
    queryset = Consolidacao.objects.select_related('programa', 'executada_por', 'ciclo')


# ---------------------------------------------------------------------------
# BENEFÍCIOS  /benefits/*
# ---------------------------------------------------------------------------
class BeneficioListView(generics.ListAPIView):
    """ GET /benefits — retorna todos os benefícios (saldos) consolidados."""
    permission_classes = [IsGestorOrSupervisor]
    serializer_class = SaldoPontosSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = SaldoPontos.objects.select_related('imovel').all().order_by('-id')
        qs = escopar_por_cidade(qs, self.request.user, 'imovel__cidade')

        imovel_id = self.request.query_params.get('imovel_id')
        if imovel_id:
            try:
                qs = qs.filter(imovel_id=int(imovel_id))
            except ValueError:
                raise ValidationError({'imovel_id': 'Deve ser um número inteiro.'})

        programa_id = self.request.query_params.get('programa_id')
        if programa_id:
            try:
                qs = qs.filter(programa_id=int(programa_id))
            except ValueError:
                raise ValidationError({'programa_id': 'Deve ser um número inteiro.'})

        ciclo = self.request.query_params.get('ciclo')
        if ciclo:
            qs = qs.filter(ciclo=ciclo)

        return qs


class BeneficioDetailView(APIView):
    """
    GET /benefits/:propertyId/:programaId — benefícios do imóvel em um programa.

    Retorna a lista completa de saldos por ciclo e o desconto total acumulado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, propertyId, programaId):
        imovel = get_object_or_404(Imovel, pk=propertyId)
        programa = get_object_or_404(Programa, pk=programaId)

        if request.user.perfil == 'morador' and imovel.titular_id != request.user.id:
            return Response({'detail': 'Sem permissão.'}, status=403)
        print(SaldoPontos.objects.filter(programa=programa))
        saldos = SaldoPontos.objects.filter(imovel=imovel, programa=programa)
        total = saldos.aggregate(total=Sum('desconto_percentual'))['total'] or Decimal('0')
        desconto_final = min(Decimal(total), programa.desconto_maximo)

        return Response({
            'imovel': imovel.inscricao,
            'titular': imovel.titular.nome,
            'programa': programa.nome,
            'desconto_total_percentual': str(desconto_final),
            'saldos_por_ciclo': SaldoPontosSerializer(saldos, many=True).data,
        })


# ---------------------------------------------------------------------------
# RELATÓRIOS  /reports/*
# ---------------------------------------------------------------------------
class ReportParticipationView(APIView):
    """ GET /reports/participation — quem participou do programa."""
    permission_classes = [IsGestorOrSupervisor]

    def get(self, request):
        from collection.models import RegistroColeta

        participantes = (
            escopar_por_cidade(RegistroColeta.objects.all(), request.user, 'imovel__cidade')
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
        
        programa_id = request.query_params.get('programa_id')
        if programa_id:
            try:
                participantes = participantes.filter(programa_id=int(programa_id))
            except ValueError:
                raise ValidationError({'programa_id': 'Deve ser um número inteiro.'})

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(participantes, request)
        if page is not None:
            return paginator.get_paginated_response(page)
        return Response(list(participantes))


class ReportCollectionsByCycleView(APIView):
    """ GET /reports/collections-by-cycle — total de coletas e pontos por ciclo. """
    permission_classes = [IsGestorOrSupervisor]

    def get(self, request):
        from collection.models import RegistroColeta

        qs = escopar_por_cidade(RegistroColeta.objects.all(), request.user, 'imovel__cidade')
        
        programa_id = request.query_params.get('programa_id')
        if not programa_id:
            return Response([])
            
        try:
            programa_id = int(programa_id)
        except ValueError:
            return Response([])

        qs = qs.filter(programa_id=programa_id)
        ciclos = Ciclo.objects.filter(programa_id=programa_id).order_by('data_inicio')

        resultado = []
        for ciclo in ciclos:
            stats = qs.filter(
                data_hora_coleta__date__gte=ciclo.data_inicio,
                data_hora_coleta__date__lte=ciclo.data_fim
            ).aggregate(
                total_coletas=Count('id'),
                total_pontos=Sum('pontuacao')
            )
            
            resultado.append({
                "ciclo_nome": ciclo.nome,
                "total_coletas": stats['total_coletas'] or 0,
                "total_pontos": stats['total_pontos'] or 0
            })

        return Response(resultado)

class ReportRankingView(APIView):
    """ GET /reports/ranking — ranking de imóveis por pontuação."""
    permission_classes = [IsGestorOrSupervisor]

    def get(self, request):
        from collection.models import RegistroColeta

        ranking = (
            escopar_por_cidade(RegistroColeta.objects.all(), request.user, 'imovel__cidade')
            .values('imovel__inscricao', 'imovel__titular__nome')
            .annotate(pontos=Sum('pontuacao'))
            .order_by('-pontos')
        )
        
        programa_id = request.query_params.get('programa_id')
        if programa_id:
            try:
                ranking = ranking.filter(programa_id=int(programa_id))
            except ValueError:
                raise ValidationError({'programa_id': 'Deve ser um número inteiro.'})

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(ranking, request)
        if page is not None:
            return paginator.get_paginated_response(page)
        return Response(list(ranking))


class ReportImpactView(APIView):
    """ GET /reports/impact — impacto agregado do programa."""
    permission_classes = [IsGestorOrSupervisor]

    def get(self, request):
        from collection.models import RegistroColeta

        coletas = escopar_por_cidade(RegistroColeta.objects.all(), request.user, 'imovel__cidade')
        saldos = escopar_por_cidade(SaldoPontos.objects.all(), request.user, 'imovel__cidade')

        programa_id = request.query_params.get('programa_id')

        # Filtra por programa se fornecido
        if programa_id:
            try:
                coletas = coletas.filter(programa_id=int(programa_id))
                saldos = saldos.filter(programa_id=int(programa_id))
            except ValueError:
                raise ValidationError({'programa_id': 'Deve ser um número inteiro.'})

        total_coletas = coletas.count()
        total_pontos = coletas.aggregate(t=Sum('pontuacao'))['t'] or 0
        total_imoveis_participantes = (
            coletas.values('imovel').distinct().count()
        )
        total_desconto_concedido = (
            saldos.aggregate(t=Sum('desconto_percentual'))['t'] or 0
        )

        return Response({
            'total_coletas': total_coletas,
            'total_pontos': total_pontos,
            'total_imoveis_participantes': total_imoveis_participantes,
            'soma_desconto_percentual': str(total_desconto_concedido),
        })


# ---------------------------------------------------------------------------
# CONSTANTE DE PONTUAÇÃO  /scoring-constant
# ---------------------------------------------------------------------------
class ConstantePontuacaoView(APIView):
    """
    GET   /scoring-constant — leitura da constante (qualquer autenticado).
    PATCH /scoring-constant — atualiza a constante (somente supervisor).
    """

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsSupervisor()]
        return [IsAuthenticated()]

    def get(self, request):
        constante = ConstantePontuacao.get_valor()
        return Response(ConstantePontuacaoSerializer(constante).data)

    def patch(self, request):
        constante = ConstantePontuacao.get_valor()
        serializer = ConstantePontuacaoSerializer(constante, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(atualizado_por=request.user)
        return Response(serializer.data)