from django.db import models
from program.models import Imovel


class RegistroColeta(models.Model):
    """
    Coleta recebida da fila RabbitMQ e registrada no Core.
    """


    id_microservico = models.CharField(max_length=50, unique=True, help_text='ID gerado pelo microserviço (MongoDB)')
    imovel = models.ForeignKey(Imovel, on_delete=models.PROTECT, related_name='coletas')
    pontuacao = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Pontuação já calculada recebida do microserviço')

    class Meta:
        ordering = ['-id_microservico']

    def __str__(self):
        return (
            f"{self.imovel.inscricao} | "
            f"Pontuação: {self.pontuacao}"
        )