from django.contrib import admin
from .models import Imovel, SaldoPontos


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = ('inscricao', 'nome_titular', 'cpf_titular', 'num_moradores', 'ativo', 'data_adesao')
    search_fields = ('inscricao', 'nome_titular', 'cpf_titular')
    list_filter = ('ativo', 'data_adesao')

@admin.register(SaldoPontos)
class SaldoPontosAdmin(admin.ModelAdmin):
    list_display = ('imovel', 'ciclo', 'desconto_percentual', 'atualizado')
    search_fields = ('imovel__inscricao', 'imovel__nome_titular')
    list_filter = ('ciclo',)
