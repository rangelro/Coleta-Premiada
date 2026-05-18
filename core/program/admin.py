from django.contrib import admin
from .models import Imovel, SaldoPontos


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = ('id', 'inscricao', 'titular', 'cidade', 'estado', 'num_moradores', 'ativo')
    search_fields = ('inscricao',)
    list_filter = ('ativo',)

@admin.register(SaldoPontos)
class SaldoPontosAdmin(admin.ModelAdmin):
    list_display = ('imovel', 'ciclo', 'desconto_percentual', 'atualizado')
    search_fields = ('imovel__inscricao', 'imovel__nome_titular')
    list_filter = ('ciclo',)
