"""
Class-Based Views do app `accounts`.

Cobre:
- /auth/*       autenticação e dados do usuário logado
- /users/*      listagem/consulta de usuários
- /roles/*      CRUD de papéis (permissões)
- /me/*         portal do cidadão (histórico, pontos, benefícios, programa)
"""
import logging
import requests as http_client

from django.conf import settings

logger = logging.getLogger(__name__)
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import Usuario, Role, Cidade
from .serializers import (
    GoogleOAuthSerializer,
    GoogleCadastroComplementarSerializer,
    UsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioSelfRegisterSerializer,
    UsuarioUpdateSerializer,
    UsuarioManagerUpdateSerializer,
    RoleSerializer,
    CidadeSerializer,
)
from .permissions import IsGestor, IsGerenteGeral, IsGestorOrSupervisor, EmailConfirmado, CadastroCompleto


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
    permission_classes = [IsAuthenticated, EmailConfirmado]
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
    """
    POST /auth — cadastro público, sempre como perfil 'morador'.

    Gestor, supervisor e gerente_geral só podem ser criados por um usuário
    já autorizado, via POST /users (UserManagerView).
    """
    permission_classes = [AllowAny]
    serializer_class = UsuarioSelfRegisterSerializer
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

        logger.info("[GoogleOAuth] Iniciando troca de código. redirect_uri=%s", redirect_uri)

        access_token = self._exchange_code(code, redirect_uri)
        if access_token is None:
            logger.error("[GoogleOAuth] _exchange_code retornou None — abortando")
            return Response(
                {'detail': 'Falha ao obter token do Google. Verifique o código ou tente novamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info("[GoogleOAuth] access_token obtido com sucesso. Buscando dados do usuário.")

        google_user = self._fetch_google_user(access_token)
        if google_user is None:
            logger.error("[GoogleOAuth] _fetch_google_user retornou None — abortando")
            return Response(
                {'detail': 'Falha ao buscar dados do usuário no Google.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info("[GoogleOAuth] Dados do usuário recebidos. email=%s", google_user.get('email'))

        usuario = self._get_or_create_usuario(google_user)
        if not usuario.ativo:
            logger.warning("[GoogleOAuth] Usuário inativo. email=%s", google_user.get('email'))
            return Response(
                {'detail': 'Conta inativa. Entre em contato com o administrador.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(usuario)
        logger.info("[GoogleOAuth] Login bem-sucedido. email=%s cadastro_completo=%s",
                    usuario.email, usuario.cadastro_completo)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'cadastro_completo': usuario.cadastro_completo,
            },
            status=status.HTTP_200_OK,
        )

    def _exchange_code(self, code: str, redirect_uri: str) -> str | None:
        logger.debug("[GoogleOAuth._exchange_code] POST %s redirect_uri=%s", self._GOOGLE_TOKEN_URL, redirect_uri)
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
            logger.debug("[GoogleOAuth._exchange_code] status=%s body=%s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
            token = resp.json().get('access_token')
            if not token:
                logger.error("[GoogleOAuth._exchange_code] Resposta OK mas sem access_token. body=%s", resp.text[:500])
            return token
        except http_client.exceptions.Timeout:
            logger.error("[GoogleOAuth._exchange_code] Timeout ao chamar %s", self._GOOGLE_TOKEN_URL)
            return None
        except http_client.exceptions.HTTPError as exc:
            logger.error("[GoogleOAuth._exchange_code] HTTPError status=%s body=%s",
                         exc.response.status_code if exc.response is not None else "?",
                         exc.response.text[:500] if exc.response is not None else "")
            return None
        except Exception:
            logger.exception("[GoogleOAuth._exchange_code] Erro inesperado")
            return None

    def _fetch_google_user(self, access_token: str) -> dict | None:
        logger.debug("[GoogleOAuth._fetch_google_user] GET %s", self._GOOGLE_USERINFO_URL)
        try:
            resp = http_client.get(
                self._GOOGLE_USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
            logger.debug("[GoogleOAuth._fetch_google_user] status=%s body=%s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
            return resp.json()
        except http_client.exceptions.Timeout:
            logger.error("[GoogleOAuth._fetch_google_user] Timeout ao chamar %s", self._GOOGLE_USERINFO_URL)
            return None
        except http_client.exceptions.HTTPError as exc:
            logger.error("[GoogleOAuth._fetch_google_user] HTTPError status=%s body=%s",
                         exc.response.status_code if exc.response is not None else "?",
                         exc.response.text[:500] if exc.response is not None else "")
            return None
        except Exception:
            logger.exception("[GoogleOAuth._fetch_google_user] Erro inesperado")
            return None

    def _get_or_create_usuario(self, google_data: dict) -> 'Usuario':
        email = google_data.get('email', '')

        usuario = Usuario.objects.filter(email=email).first()
        if not usuario:
            # Nome do Google é apenas um placeholder; o usuário irá substituí-lo
            # no formulário de cadastro complementar obrigatório.
            nome_placeholder = (
                google_data.get('given_name')
                or (google_data.get('name') or '').split()[0]
                or email.split('@')[0]
            )
            usuario = Usuario.objects.create_user(
                email=email,
                nome=nome_placeholder,
                perfil='morador',
                email_confirmado=True,
                cadastro_completo=False,
            )
        return usuario


class GoogleCadastroComplementarView(APIView):
    """
    PATCH /auth/completar-cadastro — preenche nome, sobrenome e CPF após login via Google.

    Obrigatório na primeira vez. Enquanto `cadastro_completo=False`, o acesso
    às demais áreas do sistema fica bloqueado pela permissão CadastroCompleto.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        usuario = request.user
        if usuario.cadastro_completo:
            return Response(
                {'detail': 'Cadastro complementar já foi concluído.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = GoogleCadastroComplementarSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        usuario.nome = data['nome']
        usuario.sobrenome = data['sobrenome']
        usuario.cpf = data['cpf']
        usuario.cadastro_completo = True
        usuario.save(update_fields=['nome', 'sobrenome', 'cpf', 'cadastro_completo'])

        return Response({'detail': 'Cadastro complementar concluído com sucesso.'})


from config.pagination import StandardResultsSetPagination


# ---------------------------------------------------------------------------
# CONFIRMAÇÃO DE E-MAIL
# ---------------------------------------------------------------------------
class ConfirmarEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Token obrigatório.'}, status=400)

        from django.utils import timezone
        try:
            usuario = Usuario.objects.get(token_confirmacao=token)
        except Usuario.DoesNotExist:
            return Response({'detail': 'Token inválido.'}, status=400)

        if usuario.token_expira_em < timezone.now():
            return Response({'detail': 'Token expirado. Solicite um novo.'}, status=400)

        usuario.email_confirmado = True
        usuario.token_confirmacao = None
        usuario.token_expira_em = None
        usuario.save(update_fields=['email_confirmado', 'token_confirmacao', 'token_expira_em'])
        return Response({'detail': 'E-mail confirmado com sucesso.'})


class ReenviarConfirmacaoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        usuario = request.user
        if usuario.email_confirmado:
            return Response({'detail': 'E-mail já confirmado.'}, status=400)
        from .tasks import enviar_email_confirmacao
        enviar_email_confirmacao.delay(usuario.pk)
        return Response({'detail': 'E-mail de confirmação reenviado.'})


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
# CIDADES  /cidades/*
# ---------------------------------------------------------------------------
class CidadeListCreateView(generics.ListCreateAPIView):
    """
    🔒 GET  /cidades — lista cidades atendidas (qualquer autenticado).
    🔒 POST /cidades — cadastra nova cidade (apenas gerente_geral).
    """
    serializer_class = CidadeSerializer
    queryset = Cidade.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsGerenteGeral()]
        return [IsAuthenticated()]


class CidadeDetailView(generics.RetrieveUpdateAPIView):
    """🔒 PATCH /cidades/:id — atualiza uma cidade (apenas gerente_geral)."""
    serializer_class = CidadeSerializer
    queryset = Cidade.objects.all()

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsGerenteGeral()]
        return [IsAuthenticated()]


# ---------------------------------------------------------------------------
# PORTAL DO CIDADÃO  /me/*
# ---------------------------------------------------------------------------
class MeHistoryView(APIView):
    """🔒 GET /me/history — histórico de coletas do usuário logado."""
    permission_classes = [IsAuthenticated, EmailConfirmado, CadastroCompleto]

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
    permission_classes = [IsAuthenticated, EmailConfirmado, CadastroCompleto]

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
    permission_classes = [IsAuthenticated, EmailConfirmado, CadastroCompleto]

    def get(self, request):
        from program.models import SaldoPontos
        from program.serializers import SaldoPontosSerializer

        saldos = SaldoPontos.objects.filter(imovel__titular=request.user)
        return Response(SaldoPontosSerializer(saldos, many=True).data)


class MeProgramView(APIView):
    """🔒 GET /me/program — programa atual em que o usuário está participando."""
    permission_classes = [IsAuthenticated, EmailConfirmado, CadastroCompleto]

    def get(self, request):
        from program.models import Programa
        from program.serializers import ProgramaSerializer

        programa = Programa.objects.filter(ativo=True).order_by('-data_inicio').first()
        if not programa:
            return Response({'detail': 'Nenhum programa ativo.'}, status=404)
        return Response(ProgramaSerializer(programa).data)
