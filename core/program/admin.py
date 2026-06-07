from django.contrib import admin
from .models import (
    Programa, RegraPrograma,
    Imovel, SaldoPontos,
    Consolidacao, ConstantePontuacao,
)


class RegraInline(admin.StackedInline):
    model = RegraPrograma
    extra = 0
    can_delete = False


@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data_inicio', 'data_fim', 'desconto_maximo', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    inlines = [RegraInline]
    fieldsets = (
        (None, {
            'fields': ('nome', 'descricao', 'ativo'),
        }),
        ('Vigência', {
            'fields': ('data_inicio', 'data_fim'),
        }),
        ('Benefício', {
            'fields': ('desconto_maximo',),
        }),
    )


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'inscricao', 'titular', 'cidade', 'estado',
        'num_moradores', 'latitude', 'longitude', 'geocodificacao_falhou', 'ativo',
    )
    search_fields = ('inscricao',)
    list_filter = ('ativo', 'geocodificacao_falhou')
    readonly_fields = ('latitude', 'longitude', 'geocodificacao_falhou')


@admin.register(SaldoPontos)
class SaldoPontosAdmin(admin.ModelAdmin):
    list_display = ('imovel', 'programa', 'ciclo', 'desconto_percentual', 'atualizado')
    search_fields = ('imovel__inscricao',)
    list_filter = ('programa', 'ciclo')


@admin.register(Consolidacao)
class ConsolidacaoAdmin(admin.ModelAdmin):
    list_display = ('programa', 'status', 'total_imoveis', 'total_pontos', 'executada_por', 'executada_em')
    list_filter = ('status', 'programa')
    search_fields = ('programa__nome',)
    readonly_fields = ('executada_em', 'executada_por', 'total_imoveis', 'total_pontos')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.executada_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(ConstantePontuacao)
class ConstantePontuacaoAdmin(admin.ModelAdmin):
    list_display = ('pontos_por_kg', 'atualizado_em', 'atualizado_por')
    readonly_fields = ('atualizado_em', 'atualizado_por')

    def save_model(self, request, obj, form, change):
        obj.atualizado_por = request.user
        super().save_model(request, obj, form, change)
