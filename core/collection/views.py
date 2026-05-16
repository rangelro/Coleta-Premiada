"""
Class-Based Views do app `collection`.

Cobre:
- /collections/*                   coletas registradas no Core
- /collections/:id/evidences       evidências (fotos) associadas a uma coleta
- /disputes/*                      contestações abertas pelos moradores
"""
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import (
    IsGestor, IsMorador, IsGestorOrSupervisor,
)

from .models import RegistroColeta, Evidencia, Contestacao
from .serializers import (
    RegistroColetaSerializer,
    EvidenciaSerializer,
    ContestacaoSerializer,
    ContestacaoCreateSerializer,
    ContestacaoUpdateSerializer,
)


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

    def get_queryset(self):
        qs = RegistroColeta.objects.select_related('imovel', 'imovel__titular')
        user = self.request.user
        if getattr(user, 'perfil', None) == 'morador':
            qs = qs.filter(imovel__titular=user)
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
        )
        user = self.request.user
        if getattr(user, 'perfil', None) == 'morador':
            qs = qs.filter(aberta_por=user)
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
        return obj

    def perform_update(self, serializer):
        serializer.save(analisada_por=self.request.user)
