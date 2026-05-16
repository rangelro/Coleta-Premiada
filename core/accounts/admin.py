from django.contrib import admin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'nome', 'perfil', 'ativo', 'is_staff')
    search_fields = ('email', 'nome')
    list_filter = ('perfil', 'ativo', 'is_staff')
