"""
Permissões customizadas baseadas no campo `perfil` do Usuario.

Perfis disponíveis: 'supervisor', 'morador', 'gestor', 'gerente_geral'.

`gerente_geral` é hierarquicamente superior a `gestor`: por isso as classes
que hoje representam privilégios de gestor/supervisor também aceitam
`gerente_geral`, evitando duplicar checagens em cada view.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

# Perfis com privilégios de gestor (inclui o superior gerente_geral).
PERFIS_GESTOR = ('gestor', 'gerente_geral')
# Perfis com privilégios de supervisor (inclui o superior gerente_geral).
PERFIS_SUPERVISOR = ('supervisor', 'gerente_geral')
# Perfis com privilégios administrativos (gestor, supervisor ou superior).
PERFIS_ADMINISTRATIVOS = ('gestor', 'supervisor', 'gerente_geral')


class _PerfilPermission(BasePermission):
    perfis_permitidos = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and user.ativo
            and getattr(user, 'perfil', None) in self.perfis_permitidos
        )


class IsMorador(_PerfilPermission):
    perfis_permitidos = ('morador',)


class IsGestor(_PerfilPermission):
    perfis_permitidos = PERFIS_GESTOR


class IsSupervisor(_PerfilPermission):
    perfis_permitidos = PERFIS_SUPERVISOR


class IsGerenteGeral(_PerfilPermission):
    """Ações exclusivas do usuário superior (ex: gerenciar cidades e gestores)."""
    perfis_permitidos = ('gerente_geral',)


class IsGestorOrSupervisor(_PerfilPermission):
    """Gestor, Supervisor e Gerente Geral possuem privilégios administrativos."""
    perfis_permitidos = PERFIS_ADMINISTRATIVOS


class IsOwnerOrGestor(BasePermission):
    """
    Permite acesso ao próprio titular do recurso ou a um gestor.

    A view precisa expor um método `get_owner(obj)` que retorne o usuário
    titular do recurso comparado a `request.user`.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, 'perfil', None) in PERFIS_GESTOR:
            return True
        getter = getattr(view, 'get_owner', None)
        owner = getter(obj) if callable(getter) else getattr(obj, 'titular', None)
        return owner == user


class ReadOnlyOrGestor(BasePermission):
    """Leitura para qualquer autenticado, escrita só para gestor (ou superior)."""
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.ativo):
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, 'perfil', None) in PERFIS_GESTOR
