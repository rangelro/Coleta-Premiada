from django.contrib import admin
from .models import RegistroColeta


@admin.register(RegistroColeta)
class RegistroColetaAdmin(admin.ModelAdmin):
    list_display = ('id_microservico', 'imovel', 'programa', 'peso_kg', 'pontuacao', 'data_hora_coleta')
    search_fields = ('id_microservico', 'imovel__inscricao')
    list_filter = ('programa',)
    autocomplete_fields = ('programa',)
    readonly_fields = ('foto_url',)
