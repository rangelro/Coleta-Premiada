"""
Class-Based Views do app `collection`.

Cobre:
- /collections/*           coletas registradas no Core
- /collections/images/<path>  proxy de imagens do MinIO para o browser
- /disputes/*              contestações abertas pelos moradores
"""
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError, PermissionDenied

from accounts.permissions import (
    IsGestor, IsMorador, IsGestorOrSupervisor,
)
from accounts.scoping import escopar_por_cidade, usuario_pode_ver_cidade

from .models import RegistroColeta, Contestacao
from .serializers import (
    RegistroColetaSerializer,
    ContestacaoSerializer,
    ContestacaoCreateSerializer,
    ContestacaoUpdateSerializer,
)

from config.pagination import StandardResultsSetPagination


# ---------------------------------------------------------------------------
# COLETAS  /collections/*
# ---------------------------------------------------------------------------
class ColetaListCreateView(generics.ListCreateAPIView):
    """
    🔒 GET  /collections — lista coletas.
    🔒 POST /collections — registra coleta (normalmente vinda da fila;
       restrito a gestor/supervisor para entrada manual).

    Regra de visibilidade:
    - Morador vê apenas coletas dos seus imóveis.
    - Gestor/supervisor vê todas.
    """
    serializer_class = RegistroColetaSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = RegistroColeta.objects.select_related('imovel', 'imovel__titular').all().order_by('-data_hora_coleta')
        user = self.request.user
        if getattr(user, 'perfil', None) == 'morador':
            qs = qs.filter(
                Q(imovel__titular=user) | Q(imovel__moradores=user)
            ).distinct()
        else:
            # Gestor/supervisor só enxergam coletas da própria cidade;
            # gerente_geral enxerga todas.
            qs = escopar_por_cidade(qs, user, 'imovel__cidade__nome')

        # Filtros
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

        data_inicio = self.request.query_params.get('data_inicio')
        if data_inicio:
            try:
                import datetime; datetime.date.fromisoformat(data_inicio)
            except ValueError:
                raise ValidationError({'data_inicio': 'Use o formato YYYY-MM-DD.'})
            qs = qs.filter(data_hora_coleta__date__gte=data_inicio)

        data_fim = self.request.query_params.get('data_fim')
        if data_fim:
            try:
                import datetime; datetime.date.fromisoformat(data_fim)
            except ValueError:
                raise ValidationError({'data_fim': 'Use o formato YYYY-MM-DD.'})
            qs = qs.filter(data_hora_coleta__date__lte=data_fim)

        return qs

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsGestorOrSupervisor()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        from collection.services.coleta_service import registrar_nova_coleta
        from program.models import Imovel
        from decimal import Decimal
        
        imovel_id = request.data.get('imovel')
        peso_kg = request.data.get('peso_kg')
        data_hora = request.data.get('data_hora_coleta')
        foto = request.FILES.get('foto')

        if not imovel_id or not peso_kg:
            return Response({'error': 'imovel e peso_kg são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)

        imovel = get_object_or_404(Imovel, pk=imovel_id)
        
        coleta = registrar_nova_coleta(
            imovel=imovel,
            peso_kg=Decimal(str(peso_kg)),
            data_hora=data_hora,
            registrado_por=request.user,
            foto_file=foto
        )
        serializer = self.get_serializer(coleta)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ColetaDetailView(generics.RetrieveUpdateAPIView):
    """
    🔒 GET       /collections/:id — detalhe de uma coleta.
    🔒 PUT/PATCH /collections/:id — atualiza peso e recalcula pontuação (gestor/supervisor).
    """
    serializer_class = RegistroColetaSerializer
    queryset = RegistroColeta.objects.select_related('imovel', 'imovel__titular')

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsGestorOrSupervisor()]
        return [IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        # Morador só acessa coletas dos próprios imóveis.
        if getattr(user, 'perfil', None) == 'morador' and obj.imovel.titular_id != user.id:
            self.permission_denied(self.request)
        # Gestor/supervisor só acessam coletas da própria cidade.
        if not usuario_pode_ver_cidade(user, obj.imovel.cidade.nome):
            self.permission_denied(self.request)
        return obj

    def perform_update(self, serializer):
        from program.models import ConstantePontuacao, Ciclo, RegraPrograma, SaldoPontos
        from program.business_rules import aplicar_teto
        from decimal import Decimal
        from django.utils import timezone

        coleta = serializer.instance
        peso_antigo = coleta.peso_kg

        nova_coleta = serializer.save()

        if nova_coleta.peso_kg != peso_antigo:
            constante = ConstantePontuacao.get_valor()
            pontos_por_kg = Decimal(str(constante.pontos_por_kg))
            nova_pontuacao = (nova_coleta.peso_kg * pontos_por_kg).quantize(Decimal('0.01'))
            nova_coleta.pontuacao = nova_pontuacao
            nova_coleta.save(update_fields=['pontuacao'])

            programa = nova_coleta.programa
            if programa is not None:
                hoje = nova_coleta.data_hora_coleta.date() if nova_coleta.data_hora_coleta else timezone.now().date()
                ciclo = Ciclo.objects.filter(
                    programa=programa,
                    data_inicio__lte=hoje,
                    data_fim__gte=hoje,
                    status='aberto'
                ).first()

                if ciclo:
                    regras, _ = RegraPrograma.objects.get_or_create(programa=programa)
                    saldo, _ = SaldoPontos.objects.get_or_create(
                        imovel=nova_coleta.imovel, programa=programa, ciclo=ciclo,
                        defaults={'desconto_percentual': 0}
                    )
                    # Recalcula o saldo somando todas as coletas do ciclo para evitar
                    # inconsistência quando a coleta original foi capada pelo teto de 40%.
                    total_pontuacao = RegistroColeta.objects.filter(
                        imovel=nova_coleta.imovel,
                        programa=programa,
                        data_hora_coleta__date__gte=ciclo.data_inicio,
                        data_hora_coleta__date__lte=ciclo.data_fim,
                    ).aggregate(total=Sum('pontuacao'))['total'] or Decimal('0')
                    novo_desconto_bruto = (total_pontuacao / regras.pontos_por_real).quantize(Decimal('0.01'))
                    saldo.desconto_percentual = aplicar_teto(Decimal('0'), novo_desconto_bruto)
                    saldo.save(update_fields=['desconto_percentual'])


# ---------------------------------------------------------------------------
# IMAGE PROXY  /collections/images/<path:object_key>
# ---------------------------------------------------------------------------
class ImageProxyView(APIView):
    """
    Proxy público que busca imagens no MinIO e as entrega ao browser.
    O endpoint é público (AllowAny) porque <img> tags não enviam
    Authorization header. O object key contém UUID, sendo imprevisível.
    """
    permission_classes = [AllowAny]

    def get(self, request, object_key=None):
        from collection.services.storage import get_arquivo_stream

        # Aceita ?key= como parâmetro de query string
        key = request.query_params.get('key') or object_key
        if not key:
            return Response({'error': 'Parâmetro ?key= é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)

        stream, content_type, size = get_arquivo_stream(key)
        if not stream:
            return Response({'error': 'Imagem não encontrada'}, status=status.HTTP_404_NOT_FOUND)

        response = StreamingHttpResponse(stream, content_type=content_type)
        response['Content-Length'] = size
        response['Cache-Control'] = 'public, max-age=86400'
        return response


# ---------------------------------------------------------------------------
# CONTESTAÇÕES  /disputes/*
# ---------------------------------------------------------------------------
class ContestacaoListCreateView(generics.ListCreateAPIView):
    """
    🔒 POST /disputes — morador abre contestação sobre uma coleta.
    🔒 GET  /disputes — lista contestações.
       - Morador: apenas as próprias.
       - Gestor/supervisor: todas.

    Regra do POST: a coleta precisa pertencer a um imóvel do morador logado.
    """
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ContestacaoCreateSerializer
        return ContestacaoSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsMorador()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Contestacao.objects.select_related(
            'coleta__imovel', 'aberta_por', 'analisada_por',
        ).all().order_by('-aberta_em')
        user = self.request.user
        if getattr(user, 'perfil', None) == 'morador':
            qs = qs.filter(aberta_por=user)
        else:
            # Gestor/supervisor só enxergam contestações da própria cidade;
            # gerente_geral enxerga todas.
            qs = escopar_por_cidade(qs, user, 'coleta__imovel__cidade__nome')

        # Filtros
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
            
        return qs

    def perform_create(self, serializer):
        coleta = serializer.validated_data['coleta']
        if coleta.imovel.titular_id != self.request.user.id:
            raise PermissionError('Só é possível contestar coletas dos seus imóveis.')
        serializer.save(aberta_por=self.request.user, status='aberta')


class ContestacaoDetailView(generics.RetrieveUpdateAPIView):
    """
    🔒 GET   /disputes/:id — detalhe de uma contestação.
    🔒 PATCH /disputes/:id — gestor aceita ou nega a contestação.
    """
    queryset = Contestacao.objects.select_related(
        'coleta__imovel', 'aberta_por', 'analisada_por',
    )

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ContestacaoUpdateSerializer
        return ContestacaoSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsGestor()]
        return [IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        # Morador só vê suas próprias contestações.
        if getattr(user, 'perfil', None) == 'morador' and obj.aberta_por_id != user.id:
            self.permission_denied(self.request)
        # Gestor/supervisor só acessam contestações da própria cidade.
        if not usuario_pode_ver_cidade(user, obj.coleta.imovel.cidade.nome):
            self.permission_denied(self.request)
        return obj

    def perform_update(self, serializer):
        serializer.save(analisada_por=self.request.user)
