"""
Class-Based Views do app `accounts`.

Cobre:
- /auth/*       autenticação e dados do usuário logado
- /users/*      listagem/consulta de usuários
- /roles/*      CRUD de papéis (permissões)
- /me/*         portal do cidadão (histórico, pontos, benefícios, programa)
"""
import requests as http_client

from django.conf import settings
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import Usuario, Role
from .serializers import (
    GoogleOAuthSerializer,
    UsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer,
    UsuarioManagerUpdateSerializer,
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


class GoogleOAuthLoginView(APIView):
    """
    POST /auth/google — troca o código OAuth2 do Google por tokens JWT locais.

    Fluxo esperado:
      1. Frontend redireciona o usuário para a URL de autorização do Google.
      2. Google redireciona de volta com `?code=...` para o frontend.
      3. Frontend envia { code, redirect_uri } para este endpoint.
      4. Backend troca o código pelo access_token do Google, busca os dados
         do usuário, cria ou atualiza o Usuario local e devolve o par JWT.
    """
    permission_classes = [AllowAny]

    _GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    _GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

    def post(self, request):
        serializer = GoogleOAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        redirect_uri = serializer.validated_data['redirect_uri']

        access_token = self._exchange_code(code, redirect_uri)
        if access_token is None:
            return Response(
                {'detail': 'Falha ao obter token do Google. Verifique o código ou tente novamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        google_user = self._fetch_google_user(access_token)
        if google_user is None:
            return Response(
                {'detail': 'Falha ao buscar dados do usuário no Google.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        usuario = self._get_or_create_usuario(google_user)
        if not usuario.ativo:
            return Response(
                {'detail': 'Conta inativa. Entre em contato com o administrador.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(usuario)
        return Response(
            {'access': str(refresh.access_token), 'refresh': str(refresh)},
            status=status.HTTP_200_OK,
        )

    def _exchange_code(self, code: str, redirect_uri: str) -> str | None:
        try:
            resp = http_client.post(
                self._GOOGLE_TOKEN_URL,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                },
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get('access_token')
        except Exception:
            return None

    def _fetch_google_user(self, access_token: str) -> dict | None:
        try:
            resp = http_client.get(
                self._GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def _get_or_create_usuario(self, google_data: dict) -> 'Usuario':
        email = google_data.get('email', '')
        nome = google_data.get('name', '') or email.split('@')[0]

        usuario = Usuario.objects.filter(email=email).first()
        if usuario:
            if usuario.nome != nome:
                usuario.nome = nome
                usuario.save(update_fields=['nome'])
        else:
            usuario = Usuario.objects.create_user(
                email=email,
                nome=nome,
                perfil='morador',
            )
        return usuario


from config.pagination import StandardResultsSetPagination


# ---------------------------------------------------------------------------
# GERENCIAMENTO DE USUÁRIOS (GESTORES)  /users/*
# ---------------------------------------------------------------------------
class UserManagerView(generics.ListCreateAPIView):
    """
    🔒 GET  /users — Lista, filtra e pagina usuários (só Gestor).
    🔒 POST /users — Cria um novo usuário com qualquer perfil (só Gestor).
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsGestorOrSupervisor()]
        return [IsGestor()]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def get_queryset(self):
        queryset = Usuario.objects.all().order_by('nome')
        
        # Filtros
        perfil = self.request.query_params.get('perfil')
        if perfil:
            queryset = queryset.filter(perfil=perfil)

        ativo_str = self.request.query_params.get('ativo')
        if ativo_str:
            if ativo_str.lower() == 'true':
                queryset = queryset.filter(ativo=True)
            elif ativo_str.lower() == 'false':
                queryset = queryset.filter(ativo=False)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) | Q(email__icontains=search)
            )
            
        return queryset


class UserManagerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /users/:id — Busca um usuário (só Gestor).
    PATCH  /users/:id — Altera um usuário (só Gestor).
    DELETE /users/:id — Desativa um usuário (só Gestor).
    """
    permission_classes = [IsGestor]
    queryset = Usuario.objects.all()

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return UsuarioManagerUpdateSerializer
        return UsuarioSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Validação: Gestor não pode deletar a si mesmo.
        if request.user.id == instance.id:
            return Response(
                {'detail': 'Um gestor não pode desativar a própria conta.'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Soft-delete
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=['ativo'])


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
    """🔒 POST /users/:id/roles/:roleId — vincula um papel a um usuário.
       🔒 DELETE /users/:id/roles/:roleId — remove o vínculo de um papel a um usuário.
    """
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

    def delete(self, request, id, roleId):
        try:
            usuario = Usuario.objects.get(pk=id)
            role = Role.objects.get(pk=roleId)
        except (Usuario.DoesNotExist, Role.DoesNotExist):
            return Response({'detail': 'Usuário ou papel não encontrado.'}, status=404)

        if not usuario.roles.filter(pk=roleId).exists():
            return Response({'detail': 'Vínculo não encontrado.'}, status=404)

        usuario.roles.remove(role)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
