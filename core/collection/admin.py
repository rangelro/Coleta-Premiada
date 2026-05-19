from django.contrib import admin
from .models import RegistroColeta


@admin.register(RegistroColeta)
class RegistroColetaAdmin(admin.ModelAdmin):
    list_display = ('id_microservico', 'imovel', 'pontuacao')
    search_fields = ('id_microservico',)
    # list_filter = ('data_hora_coleta',)
