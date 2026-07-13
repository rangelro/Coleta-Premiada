from rest_framework import serializers
from .models import (
    Programa, RegraPrograma,
    Imovel, SaldoPontos, Consolidacao,
    ConstantePontuacao, Ciclo,
)


class CicloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ciclo
        fields = ['id', 'programa', 'nome', 'tipo', 'data_inicio', 'data_fim', 'status', 'criado_em']
        read_only_fields = ['id', 'criado_em']

    def validate(self, data):
        data_inicio = data.get('data_inicio', getattr(self.instance, 'data_inicio', None))
        data_fim = data.get('data_fim', getattr(self.instance, 'data_fim', None))
        programa = data.get('programa', getattr(self.instance, 'programa', None))

        if data_inicio and data_fim and data_fim < data_inicio:
            raise serializers.ValidationError('data_fim deve ser maior ou igual a data_inicio.')

        if programa and data_inicio and data_fim:
            sobrepostos = Ciclo.objects.filter(
                programa=programa,
                data_inicio__lte=data_fim,
                data_fim__gte=data_inicio,
            ).exclude(pk=self.instance.pk if self.instance else None)
            if sobrepostos.exists():
                raise serializers.ValidationError(
                    'Já existe um ciclo com datas sobrepostas para este programa.'
                )
        return data


class ImovelSerializer(serializers.ModelSerializer):
    titular_nome = serializers.CharField(source='titular.nome', read_only=True)
    cidade_nome = serializers.CharField(source='cidade.nome', read_only=True)
    cidade_uf = serializers.CharField(source='cidade.uf', read_only=True)

    class Meta:
        model = Imovel
        fields = [
            'id', 'inscricao', 'titular', 'titular_nome', 'cep', 'logradouro', 'numero',
            'complemento', 'bairro', 'cidade', 'cidade_nome', 'cidade_uf', 'estado',
            'num_moradores', 'latitude', 'longitude', 'geocodificacao_falhou',
            'ativo', 'data_adesao',
        ]
        read_only_fields = ['id', 'data_adesao', 'latitude', 'longitude', 'geocodificacao_falhou',
                            'cidade_nome', 'cidade_uf']

    def validate_titular(self, value):
        if getattr(value, 'perfil', None) != 'morador':
            raise serializers.ValidationError(
                'O titular do imóvel precisa ter perfil "morador".'
            )
        return value

    def validate_cidade(self, value):
        if not value.ativo:
            raise serializers.ValidationError(
                'Cidade inativa. Selecione uma das cidades disponíveis.'
            )
        return value



class RegraProgramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegraPrograma
        fields = ['pontos_por_real', 'minimo_para_beneficio', 'permite_acumulo_ciclos']


class ProgramaSerializer(serializers.ModelSerializer):
    regras = RegraProgramaSerializer(read_only=True)
    cidade_nome = serializers.CharField(source='cidade.nome', read_only=True)

    class Meta:
        model = Programa
        fields = [
            'id', 'nome', 'descricao', 'cidade', 'cidade_nome',
            'data_inicio', 'data_fim', 'ativo', 'desconto_maximo', 'regras',
        ]
        read_only_fields = ['id', 'cidade_nome']

    def validate(self, data):
        if data.get('data_fim') and data.get('data_inicio') \
                and data['data_fim'] < data['data_inicio']:
            raise serializers.ValidationError(
                'data_fim deve ser posterior a data_inicio.'
            )

        request = self.context.get('request')
        if request and getattr(request.user, 'perfil', None) == 'gestor':
            cidade = data.get('cidade', getattr(self.instance, 'cidade', None))
            if cidade is None:
                raise serializers.ValidationError(
                    {'cidade': 'Cidade é obrigatória para gestor.'}
                )
            if not request.user.cidade_id or request.user.cidade_id != cidade.pk:
                raise serializers.ValidationError(
                    {'cidade': 'O gestor só pode criar ou editar programas da própria cidade.'}
                )

        return data


class SaldoPontosSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaldoPontos
        fields = ['id', 'imovel', 'programa', 'ciclo', 'desconto_percentual', 'atualizado']
        read_only_fields = ['id', 'atualizado']


class ConsolidacaoSerializer(serializers.ModelSerializer):
    programa_nome = serializers.CharField(source='programa.nome', read_only=True)
    executada_por_nome = serializers.CharField(source='executada_por.nome', read_only=True)
    ciclo_nome = serializers.CharField(source='ciclo.nome', read_only=True)

    class Meta:
        model = Consolidacao
        fields = [
            'id', 'programa', 'programa_nome', 'ciclo', 'ciclo_nome', 'executada_em', 'executada_por',
            'executada_por_nome', 'status', 'total_imoveis', 'total_pontos', 'observacao',
        ]
        read_only_fields = [
            'id', 'executada_em', 'executada_por', 'status',
            'total_imoveis', 'total_pontos',
        ]


class ConstantePontuacaoSerializer(serializers.ModelSerializer):
    atualizado_por = serializers.SerializerMethodField()

    class Meta:
        model = ConstantePontuacao
        fields = ['pontos_por_kg', 'atualizado_em', 'atualizado_por']
        read_only_fields = ['atualizado_em', 'atualizado_por']
        
    def get_atualizado_por(self, obj):
        if obj.atualizado_por:
            return {
                "id": obj.atualizado_por.id,
                "email": obj.atualizado_por.email,
                "nome": obj.atualizado_por.nome if hasattr(obj.atualizado_por, 'nome') else None
            }
        return None
