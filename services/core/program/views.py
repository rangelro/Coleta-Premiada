from rest_framework import generics
from .models import Imovel
from .serializers import ImovelSerializer
from infra.rabbitmq.producer import publish_morador

# API para cadastro de imóvel (API porque vai receber cadastro via HTTP)
class ImovelCreateAPIView(generics.CreateAPIView):
    queryset = Imovel.objects.all()
    serializer_class = ImovelSerializer

    def perform_create(self, serializer):
        imovel = serializer.save()
        
        # Publica evento de adesão na fila RabbitMQ
        dados_morador = {
            "inscricao_imobiliaria": imovel.inscricao,
            "nome": imovel.nome_titular,
            "cpf": imovel.cpf_titular,
            "endereco": imovel.endereco,
            "acao": "adesao_programa"
        }
        
        try:
            publish_morador(dados_morador)
        except Exception as e:
            print(f"Erro ao publicar na fila: {e}")
