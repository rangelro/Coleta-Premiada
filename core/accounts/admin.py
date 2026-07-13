from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Role, Cidade


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario

    # Colunas exibidas na listagem
    list_display = ('email', 'nome', 'perfil', 'cidade', 'ativo', 'is_staff')
    list_filter = ('perfil', 'cidade', 'ativo', 'is_staff')
    search_fields = ('email', 'nome', 'cpf')
    ordering = ('email',)

    # Seções do formulário de EDIÇÃO
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Dados Pessoais', {
            'fields': ('nome', 'cpf')
        }),
        ('Perfil e Acesso', {
            'fields': ('perfil', 'cidade', 'ativo', 'is_staff', 'is_superuser', 'email_confirmado')
        }),
    )

    # Seções do formulário de CRIAÇÃO
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'cpf', 'perfil', 'cidade', 'password1', 'password2'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo', 'descricao')
    list_filter = ('ativo',)
    search_fields = ('nome',)


@admin.register(Cidade)
class CidadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf', 'ativo')
    list_filter = ('uf', 'ativo')
    search_fields = ('nome',)
