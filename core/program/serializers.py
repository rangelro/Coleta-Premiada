from rest_framework import serializers
from .models import (
    Programa, RegraPrograma,
    Imovel, SaldoPontos, Consolidacao,
    ConstantePontuacao,
)


class ImovelSerializer(serializers.ModelSerializer):
    #Adicionados campos para a leitura dos dados do titular pelo front
    titular_nome = serializers.CharField(source='titular.nome', read_only=True)

    class Meta:
        model = Imovel
        fields = [
            'id', 'inscricao', 'titular', 'titular_nome', 'cep', 'logradouro', 'numero',
            'complemento', 'bairro', 'cidade', 'estado', 'num_moradores',
            'latitude', 'longitude', 'geocodificacao_falhou',
            'ativo', 'data_adesao',
        ]
        read_only_fields = ['id', 'data_adesao', 'latitude', 'longitude', 'geocodificacao_falhou']

    def validate_titular(self, value):
        if getattr(value, 'perfil', None) != 'morador':
            raise serializers.ValidationError(
                'O titular do imóvel precisa ter perfil "morador".'
            )
        return value



class RegraProgramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegraPrograma
        fields = ['pontos_por_real', 'minimo_para_beneficio', 'permite_acumulo_ciclos']


class ProgramaSerializer(serializers.ModelSerializer):
    regras = RegraProgramaSerializer(read_only=True)

    class Meta:
        model = Programa
        fields = [
            'id', 'nome', 'descricao', 'data_inicio', 'data_fim',
            'ativo', 'desconto_maximo', 'regras',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        if data.get('data_fim') and data.get('data_inicio') \
                and data['data_fim'] < data['data_inicio']:
            raise serializers.ValidationError(
                'data_fim deve ser posterior a data_inicio.'
            )
        return data


class SaldoPontosSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaldoPontos
        fields = ['id', 'imovel', 'programa', 'ciclo', 'desconto_percentual', 'atualizado']
        read_only_fields = ['id', 'atualizado']


class ConsolidacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consolidacao
        fields = [
            'id', 'programa', 'executada_em', 'executada_por',
            'status', 'total_imoveis', 'total_pontos', 'observacao',
        ]
        read_only_fields = [
            'id', 'executada_em', 'executada_por', 'status',
            'total_imoveis', 'total_pontos',
        ]


class ConstantePontuacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConstantePontuacao
        fields = ['pontos_por_kg', 'atualizado_em', 'atualizado_por']
        read_only_fields = ['atualizado_em', 'atualizado_por']
