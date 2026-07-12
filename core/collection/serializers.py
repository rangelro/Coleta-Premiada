from rest_framework import serializers
from .models import RegistroColeta, Evidencia, Contestacao


class RegistroColetaSerializer(serializers.ModelSerializer):
    #Adicionados campos para a leitura dos dados do imovel e programa pelo front
    imovel_inscricao = serializers.CharField(source='imovel.inscricao', read_only=True)
    titular_nome = serializers.CharField(source='imovel.titular.nome', read_only=True)
    programa_nome = serializers.CharField(source='programa.nome', read_only=True)

    class Meta:
        model = RegistroColeta
        fields = [
            'id', 'id_microservico', 'imovel', 'imovel_inscricao', 'titular_nome',
            'programa', 'programa_nome', 'pontuacao', 'data_hora_coleta', 'peso_kg',
            'registrado_por'
        ]
        read_only_fields = ['id', 'id_microservico', 'pontuacao', 'registrado_por']


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
    morador_nome = serializers.CharField(source='aberta_por.nome', read_only=True)
    imovel_inscricao = serializers.CharField(source='coleta.imovel.inscricao', read_only=True)
    coleta_peso = serializers.CharField(source='coleta.peso_kg', read_only=True)
    coleta_data = serializers.DateTimeField(source='coleta.data_hora_coleta', read_only=True)
    coleta_pontuacao = serializers.CharField(source='coleta.pontuacao', read_only=True)

    class Meta:
        model = Contestacao
        fields = [
            'id', 'coleta', 'aberta_por', 'motivo', 'status',
            'analisada_por', 'resposta', 'aberta_em', 'atualizada_em',
            'morador_nome', 'imovel_inscricao', 'coleta_peso', 'coleta_data', 'coleta_pontuacao'
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
