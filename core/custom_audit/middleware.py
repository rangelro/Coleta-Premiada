import re
import logging
from django.contrib.auth import get_user_model
from .models import AuditLog
from .request_store import set_current_request, clear_current_request, get_client_ip

logger = logging.getLogger(__name__)


def identify_select_operation(request, user):
    """
    Identifica se o caminho da requisição aponta para algum dos modelos principais para leitura (SELECT).
    Retorna (nome_tabela, objeto_id) se correspondido, senão (None, None).
    """
    path = request.path
    path_clean = path.rstrip('/')

    # Usuários (Usuario)
    if path_clean == '/api/accounts/auth/me':
        tabela = 'accounts_usuario'
        objeto_id = str(user.id) if user and not user.is_anonymous else None
        return tabela, objeto_id
        
    m_user = re.match(r'^/api/accounts/users(?:/(\d+))?$', path_clean)
    if m_user:
        tabela = 'accounts_usuario'
        objeto_id = m_user.group(1)
        return tabela, objeto_id
        
    # Imóveis (Imovel)
    m_prop = re.match(r'^/api/program/properties(?:/(\d+))?$', path_clean)
    if m_prop:
        tabela = 'program_imovel'
        objeto_id = m_prop.group(1)
        return tabela, objeto_id

    # Programas (Programa)
    m_prog = re.match(r'^/api/program/programs(?:/(\d+))?$', path_clean)
    if m_prog:
        tabela = 'program_programa'
        objeto_id = m_prog.group(1)
        return tabela, objeto_id

    # Coletas (RegistroColeta)
    m_coll = re.match(r'^/api/collection/collections(?:/(\d+))?$', path_clean)
    if m_coll:
        tabela = 'collection_registrocoleta'
        objeto_id = m_coll.group(1)
        return tabela, objeto_id

    return None, None


class CustomAuditMiddleware:
    """
    Middleware que gerencia o contexto da requisição atual e audita operações de leitura (SELECT).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Define o contexto da requisição atual
        set_current_request(request)

        try:
            # 2. Processa a requisição
            response = self.get_response(request)
        finally:
            # Garante que o contexto da requisição seja limpo
            clear_current_request()

        # 3. Processa a auditoria de leitura após a resposta
        if request.method == 'GET' and 200 <= response.status_code < 300:
            user = request.user
            # Tenta resolver o usuário JWT caso request.user não tenha sido autenticado ainda (comum no DRF)
            if not user or user.is_anonymous:
                try:
                    from rest_framework_simplejwt.authentication import JWTAuthentication
                    auth_result = JWTAuthentication().authenticate(request)
                    if auth_result:
                        user = auth_result[0]
                except Exception:
                    pass

            tabela, objeto_id = identify_select_operation(request, user)
            if tabela:
                usuario_id = None
                usuario_email = None
                if user and not user.is_anonymous:
                    usuario_id = user.id
                    usuario_email = user.email

                ip_origem = get_client_ip(request)
                endpoint = request.path

                try:
                    AuditLog.objects.create(
                        usuario_id=usuario_id,
                        usuario_email=usuario_email,
                        operacao='SELECT',
                        tabela=tabela,
                        objeto_id=objeto_id,
                        dados_antes=None,
                        dados_depois=None,
                        ip_origem=ip_origem,
                        endpoint=endpoint
                    )
                except Exception as e:
                    logger.error(f"Falha ao registrar log de auditoria de SELECT: {e}")

        return response
