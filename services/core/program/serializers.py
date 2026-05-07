from rest_framework import serializers
from .models import Imovel

# Serializer do modelo Imovel para criação via POST pra API que vai receber os dados do cadastro
class ImovelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imovel
        fields = ['inscricao', 'cpf_titular', 'nome_titular', 'endereco', 'num_moradores']
