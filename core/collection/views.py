"""
Class-Based Views do app `collection`.

Cobre:
- /collections/*                   coletas registradas no Core
- /collections/:id/evidences       evidências (fotos) associadas a uma coleta
- /disputes/*                      contestações abertas pelos moradores
"""
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from accounts.permissions import (
    IsGestor, IsMorador, IsGestorOrSupervisor,
)
from accounts.scoping import escopar_por_cidade, usuario_pode_ver_cidade

from .models import RegistroColeta, Evidencia, Contestacao
from .serializers import (
    RegistroColetaSerializer,
    EvidenciaSerializer,
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
            qs = escopar_por_cidade(qs, user, 'imovel__cidade')

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


class ColetaDetailView(generics.RetrieveAPIView):
    """🔒 GET /collections/:id — detalhe de uma coleta."""
    permission_classes = [IsAuthenticated]
    serializer_class = RegistroColetaSerializer
    queryset = RegistroColeta.objects.select_related('imovel', 'imovel__titular')

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        # Morador só acessa coletas dos próprios imóveis.
        if getattr(user, 'perfil', None) == 'morador' and obj.imovel.titular_id != user.id:
            self.permission_denied(self.request)
        # Gestor/supervisor só acessam coletas da própria cidade.
        if not usuario_pode_ver_cidade(user, obj.imovel.cidade):
            self.permission_denied(self.request)
        return obj


# ---------------------------------------------------------------------------
# EVIDÊNCIAS  /collections/:id/evidences
# ---------------------------------------------------------------------------
class EvidenciaListCreateView(generics.ListCreateAPIView):
    """
    🔒 GET  /collections/:id/evidences — lista evidências da coleta.
    🔒 POST /collections/:id/evidences — anexa nova evidência.

    Quem pode anexar:
    - gestor, supervisor (qualquer evidência);
    - morador, apenas para coletas dos seus próprios imóveis.
    """
    serializer_class = EvidenciaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Evidencia.objects.filter(coleta_id=self.kwargs['id'])

    def perform_create(self, serializer):
        coleta = get_object_or_404(RegistroColeta, pk=self.kwargs['id'])
        user = self.request.user

        if user.perfil == 'morador' and coleta.imovel.titular_id != user.id:
            raise PermissionError('Morador só pode anexar evidência em coleta própria.')

        serializer.save(coleta=coleta, enviada_por=user)


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
            'coleta', 'aberta_por', 'analisada_por',
        ).all().order_by('-aberta_em')
        user = self.request.user
        if getattr(user, 'perfil', None) == 'morador':
            qs = qs.filter(aberta_por=user)
        else:
            # Gestor/supervisor só enxergam contestações da própria cidade;
            # gerente_geral enxerga todas.
            qs = escopar_por_cidade(qs, user, 'coleta__imovel__cidade')

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
        'coleta', 'aberta_por', 'analisada_por',
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
        if not usuario_pode_ver_cidade(user, obj.coleta.imovel.cidade):
            self.permission_denied(self.request)
        return obj

    def perform_update(self, serializer):
        serializer.save(analisada_por=self.request.user)
