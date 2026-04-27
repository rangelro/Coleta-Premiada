from django.db import models


class Pesagem(models.Model):
    """
    Representa um registro de coleta seletiva feito pelo coletor.
    Persiste no MongoDB antes de ser enviado para a fila.
    """
    MATERIAIS = [
        ('papel', 'Papel/Papelão'),
        ('plastico', 'Plástico'),
        ('aluminio', 'Alumínio'),
        ('vidro', 'Vidro'),
        ('metal', 'Metal'),
        ('eletronico', 'Eletrônico'),
    ]

    STATUS = [
        ('pendente', 'Pendente de envio para fila'),
        ('publicado', 'Publicado na fila'),
        ('erro', 'Erro ao publicar'),
    ]

    inscricao_imobiliaria = models.CharField(max_length=50)
    material = models.CharField(max_length=20, choices=MATERIAIS)
    peso_kg = models.DecimalField(max_digits=8, decimal_places=3)
    agente_id = models.CharField(max_length=50)
    data_hora = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default='pendente'
    )
    foto_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['-data_hora']

    def __str__(self):
        return f"{self.inscricao_imobiliaria} | {self.material} | {self.peso_kg}kg"