from django.db import models
from program.models import Imovel


class RegistroColeta(models.Model):
    """
    Coleta recebida da fila RabbitMQ e registrada no Core.
    """


    id_microservico = models.CharField(max_length=50, unique=True, help_text='ID gerado pelo microserviço (MongoDB)')
    imovel = models.ForeignKey(Imovel, on_delete=models.PROTECT, related_name='coletas', null=True)
    inscricao_imobiliaria = models.CharField(max_length=50)
    pontuacao = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Pontuação já calculada recebida do microserviço')
    data_hora_coleta = models.DateTimeField()
    data_hora_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_hora_coleta']

    def __str__(self):
        return (
            f"{self.inscricao_imobiliaria} | "
            f"Pontuação: {self.pontuacao}"
        )