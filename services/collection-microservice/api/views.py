from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Pesagem
from .services.fila import publicar_pesagem


class RegistrarPesagemView(APIView):
    """
    POST /api/pesagens/
    Recebe uma pesagem, salva no MongoDB e publica na fila.
    """

    def post(self, request):
        dados = request.data

        # Validação mínima
        campos = ['inscricao_imobiliaria', 'material', 'peso_kg', 'agente_id']
        for campo in campos:
            if campo not in dados:
                return Response(
                    {'erro': f'Campo obrigatório ausente: {campo}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Persiste no MongoDB
        pesagem = Pesagem.objects.create(
            inscricao_imobiliaria=dados['inscricao_imobiliaria'],
            material=dados['material'],
            peso_kg=dados['peso_kg'],
            agente_id=dados['agente_id'],
            foto_url=dados.get('foto_url'),
        )

        # Publica na fila RabbitMQ
        payload = {
            'id':                    str(pesagem.pk),
            'inscricao_imobiliaria': pesagem.inscricao_imobiliaria,
            'material':              pesagem.material,
            'peso_kg':               str(pesagem.peso_kg),
            'agente_id':             pesagem.agente_id,
            'data_hora':             pesagem.data_hora.isoformat(),
        }

        publicado = publicar_pesagem(payload)

        # Valida o status de publicação
        pesagem.status = 'publicado' if publicado else 'erro'
        pesagem.save()

        # Retorna a resposta
        return Response(
            {'id': str(pesagem.pk), 'status': pesagem.status},
            status=status.HTTP_201_CREATED
        )