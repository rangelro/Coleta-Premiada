from rest_framework import serializers
from .models import RegistroColeta, Evidencia, Contestacao


class RegistroColetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroColeta
        fields = [
            'id', 'id_microservico', 'imovel', 'programa', 'pontuacao',
            'data_hora_coleta', 'peso_kg',
        ]
        read_only_fields = ['id']


class EvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencia
        fields = ['id', 'coleta', 'descricao', 'arquivo_url', 'enviada_em', 'enviada_por']
        read_only_fields = ['id', 'enviada_em', 'enviada_por', 'coleta']


class ContestacaoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contestacao
        fields = ['coleta', 'motivo']


class ContestacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contestacao
        fields = [
            'id', 'coleta', 'aberta_por', 'motivo', 'status',
            'analisada_por', 'resposta', 'aberta_em', 'atualizada_em',
        ]
        read_only_fields = [
            'id', 'aberta_por', 'analisada_por',
            'aberta_em', 'atualizada_em',
        ]


class ContestacaoUpdateSerializer(serializers.ModelSerializer):
    """Usado pelo gestor para responder a contestação."""
    class Meta:
        model = Contestacao
        fields = ['status', 'resposta']

    def validate_status(self, value):
        if value not in ('em_analise', 'aceita', 'negada'):
            raise serializers.ValidationError(
                'Status inválido. Use: em_analise, aceita ou negada.'
            )
        return value
