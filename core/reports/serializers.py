from rest_framework import serializers

from .models import RelatorioLLM


class PeriodoInputSerializer(serializers.Serializer):
    inicio = serializers.DateField()
    fim = serializers.DateField()

    def validate(self, data):
        if data['fim'] < data['inicio']:
            raise serializers.ValidationError('fim deve ser posterior ou igual a inicio.')
        return data


class RelatorioLLMRequestSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=[t[0] for t in RelatorioLLM.TIPOS])
    periodo = PeriodoInputSerializer()
    programa_id = serializers.IntegerField(required=False, allow_null=True)


class RelatorioLLMSerializer(serializers.ModelSerializer):
    periodo = serializers.SerializerMethodField()

    class Meta:
        model = RelatorioLLM
        fields = [
            'id', 'tipo', 'periodo', 'programa',
            'relatorio', 'tokens_utilizados', 'gerado_em', 'gerado_por',
        ]
        read_only_fields = [
            'id', 'relatorio', 'tokens_utilizados', 'gerado_em', 'gerado_por',
        ]

    def get_periodo(self, obj):
        return {'inicio': obj.periodo_inicio.isoformat(), 'fim': obj.periodo_fim.isoformat()}
