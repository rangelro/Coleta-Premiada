from django.contrib import admin
from .models import RegistroColeta


@admin.register(RegistroColeta)
class RegistroColetaAdmin(admin.ModelAdmin):
    list_display = ('id_microservico', 'inscricao_imobiliaria', 'imovel', 'pontuacao', 'data_hora_coleta')
    search_fields = ('id_microservico', 'inscricao_imobiliaria')
    list_filter = ('data_hora_coleta',)
