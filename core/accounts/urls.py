from django.urls import path
from .views import (
    LogoutView,
    AuthMeView,
    AuthCreateView,
    UsuarioListView,
    UsuarioDetailView,
    RoleListCreateView,
    RoleDetailView,
    UsuarioRoleAddView,
    MeHistoryView,
    MePointsView,
    MeBenefitsView,
    MeProgramView,
)

urlpatterns = [
    # /auth
    path('auth/logout',          LogoutView.as_view(),       name='auth-logout'),
    path('auth/me',              AuthMeView.as_view(),       name='auth-me'),
    path('auth',                 AuthCreateView.as_view(),   name='auth-create'),

    # /users
    path('users',                UsuarioListView.as_view(),  name='users-list'),
    path('users/<int:pk>',       UsuarioDetailView.as_view(), name='users-detail'),

    # /roles
    path('roles',                RoleListCreateView.as_view(), name='roles-list-create'),
    path('roles/<int:pk>',       RoleDetailView.as_view(),     name='roles-detail'),
    path('users/<int:id>/roles/<int:roleId>',
         UsuarioRoleAddView.as_view(), name='users-roles-add'),

    # /me  (portal do cidadão)
    path('me/history',           MeHistoryView.as_view(),    name='me-history'),
    path('me/points',            MePointsView.as_view(),     name='me-points'),
    path('me/benefits',          MeBenefitsView.as_view(),   name='me-benefits'),
    path('me/program',           MeProgramView.as_view(),    name='me-program'),
]
