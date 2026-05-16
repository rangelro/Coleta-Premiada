"""
Permissões customizadas baseadas no campo `perfil` do Usuario.

Perfis disponíveis: 'supervisor', 'morador', 'gestor'.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class _PerfilPermission(BasePermission):
    perfil_requerido = None

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and user.ativo
            and getattr(user, 'perfil', None) == self.perfil_requerido
        )


class IsMorador(_PerfilPermission):
    perfil_requerido = 'morador'


class IsGestor(_PerfilPermission):
    perfil_requerido = 'gestor'


class IsSupervisor(_PerfilPermission):
    perfil_requerido = 'supervisor'


class IsGestorOrSupervisor(BasePermission):
    """Gestor e Supervisor possuem privilégios administrativos."""
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and user.ativo
            and getattr(user, 'perfil', None) in ('gestor', 'supervisor')
        )


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
        if getattr(user, 'perfil', None) == 'gestor':
            return True
        getter = getattr(view, 'get_owner', None)
        owner = getter(obj) if callable(getter) else getattr(obj, 'titular', None)
        return owner == user


class ReadOnlyOrGestor(BasePermission):
    """Leitura para qualquer autenticado, escrita só para gestor."""
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.ativo):
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, 'perfil', None) == 'gestor'
