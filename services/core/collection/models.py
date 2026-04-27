from django.db import models
from program.models import Imovel


class RegistroColeta(models.Model):
    """
    Coleta recebida da fila RabbitMQ e registrada no Core.
    Cada registro gera crédito de desconto no IPTU do imóvel.
    """
    MATERIAIS = [
        ('papel', 'Papel/Papelão'),
        ('plastico', 'Plástico'),
        ('aluminio', 'Alumínio'),
        ('vidro', 'Vidro'),
        ('metal', 'Metal'),
        ('eletronico', 'Eletrônico'),
    ]

    id_microservico = models.CharField(
        max_length=50, unique=True,
        help_text='ID gerado pelo microserviço (MongoDB)'
    )
    imovel = models.ForeignKey(
        Imovel, on_delete=models.PROTECT,
        related_name='coletas', null=True
    )
    inscricao_imobiliaria = models.CharField(max_length=50)
    material = models.CharField(max_length=20, choices=MATERIAIS)
    peso_kg = models.DecimalField(max_digits=8, decimal_places=3)
    agente_id = models.CharField(max_length=50)
    desconto_gerado = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Pontos percentuais de desconto no IPTU gerados'
    )
    data_hora_coleta = models.DateTimeField()
    data_hora_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_hora_coleta']

    def __str__(self):
        return (
            f"{self.inscricao_imobiliaria} | "
            f"{self.material} | {self.peso_kg}kg | "
            f"{self.desconto_gerado}%"
        )