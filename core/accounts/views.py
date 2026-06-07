"""
Class-Based Views do app `accounts`.

Cobre:
- /auth/*       autenticação e dados do usuário logado
- /users/*      listagem/consulta de usuários
- /roles/*      CRUD de papéis (permissões)
- /me/*         portal do cidadão (histórico, pontos, benefícios, programa)
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import Usuario, Role
from .serializers import (
    UsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer,
    RoleSerializer,
)
from .permissions import IsGestor, IsGestorOrSupervisor


# ---------------------------------------------------------------------------
# AUTENTICAÇÃO  /auth/*
# ---------------------------------------------------------------------------
class LogoutView(APIView):
    """🔒 POST /auth/logout — invalida o refresh token do usuário logado."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('refresh')
        if not token:
            return Response(
                {'detail': 'Refresh token obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            return Response(
                {'detail': 'Token inválido ou já expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthMeView(generics.RetrieveUpdateDestroyAPIView):
    """
    🔒 GET    /auth/me — retorna dados do usuário logado.
    🔒 PATCH  /auth/me — atualiza dados do próprio usuário.
    🔒 DELETE /auth/me — encerra (desativa) a conta do usuário logado.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UsuarioSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    def perform_destroy(self, instance):
        # Soft-delete: respeita a regra de auditoria e mantém histórico.
        instance.ativo = False
        instance.save(update_fields=['ativo'])


class AuthCreateView(generics.CreateAPIView):
    """POST /auth — cria um novo usuário."""
    permission_classes = [AllowAny]
    serializer_class = UsuarioCreateSerializer
    queryset = Usuario.objects.all()


# ---------------------------------------------------------------------------
# USUÁRIOS  /users/*
# ---------------------------------------------------------------------------
class UsuarioListView(generics.ListAPIView):
    """🔒 GET /users — busca todos os usuários (gestor/supervisor)."""
    permission_classes = [IsGestorOrSupervisor]
    serializer_class = UsuarioSerializer
    queryset = Usuario.objects.filter(ativo=True).order_by('nome')


class UsuarioDetailView(generics.RetrieveAPIView):
    """🔒 GET /users/:id — busca um único usuário."""
    permission_classes = [IsAuthenticated]
    serializer_class = UsuarioSerializer
    queryset = Usuario.objects.all()


# ---------------------------------------------------------------------------
# ROLES (PERMISSÕES)  /roles/*
# ---------------------------------------------------------------------------
class RoleListCreateView(generics.ListCreateAPIView):
    """
    🔒 GET  /roles — lista todos os papéis.
    🔒 POST /roles — cria um novo papel (apenas gestor).
    """
    serializer_class = RoleSerializer
    queryset = Role.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsGestor()]
        return [IsAuthenticated()]


class RoleDetailView(generics.RetrieveUpdateAPIView):
    """🔒 PATCH /roles/:id — atualiza um papel (apenas gestor)."""
    serializer_class = RoleSerializer
    queryset = Role.objects.all()

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsGestor()]
        return [IsAuthenticated()]


class UsuarioRoleAddView(APIView):
    """🔒 POST /users/:id/roles/:roleId — vincula um papel a um usuário."""
    permission_classes = [IsGestor]

    def post(self, request, id, roleId):
        try:
            usuario = Usuario.objects.get(pk=id)
            role = Role.objects.get(pk=roleId, ativo=True)
        except Usuario.DoesNotExist:
            return Response({'detail': 'Usuário não encontrado.'}, status=404)
        except Role.DoesNotExist:
            return Response({'detail': 'Papel não encontrado ou inativo.'}, status=404)

        usuario.roles.add(role)
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# PORTAL DO CIDADÃO  /me/*
# ---------------------------------------------------------------------------
class MeHistoryView(APIView):
    """🔒 GET /me/history — histórico de coletas do usuário logado."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Importação local para evitar ciclo entre apps.
        from collection.models import RegistroColeta
        from collection.serializers import RegistroColetaSerializer

        coletas = (
            RegistroColeta.objects
            .filter(imovel__titular=request.user)
            .select_related('imovel')
        )
        return Response(RegistroColetaSerializer(coletas, many=True).data)


class MePointsView(APIView):
    """🔒 GET /me/points — total de pontuação acumulada do usuário logado."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum
        from collection.models import RegistroColeta

        total = (
            RegistroColeta.objects
            .filter(imovel__titular=request.user)
            .aggregate(total=Sum('pontuacao'))['total'] or 0
        )
        return Response({'pontos_acumulados': total})


class MeBenefitsView(APIView):
    """🔒 GET /me/benefits — benefícios (saldos) do usuário logado."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from program.models import SaldoPontos
        from program.serializers import SaldoPontosSerializer

        saldos = SaldoPontos.objects.filter(imovel__titular=request.user)
        return Response(SaldoPontosSerializer(saldos, many=True).data)


class MeProgramView(APIView):
    """🔒 GET /me/program — programa atual em que o usuário está participando."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from program.models import Programa
        from program.serializers import ProgramaSerializer

        programa = Programa.objects.filter(ativo=True).order_by('-data_inicio').first()
        if not programa:
            return Response({'detail': 'Nenhum programa ativo.'}, status=404)
        return Response(ProgramaSerializer(programa).data)
