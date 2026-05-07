from django.db import models
from django.core.validators import MinValueValidator


class Imovel(models.Model):
    """Unidade imobiliária participante do programa."""
    MATERIAIS = [
        ('papel', 'Papel/Papelão'),
        ('plastico', 'Plástico'),
        ('aluminio', 'Alumínio'),
        ('vidro', 'Vidro'),
        ('metal', 'Metal'),
        ('eletronico', 'Eletrônico'),
    ]

    inscricao = models.CharField(max_length=50, unique=True)
    cpf_titular = models.CharField(max_length=14)
    nome_titular = models.CharField(max_length=150)
    endereco = models.CharField(max_length=255)
    num_moradores = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Quantidade de moradores na residência'
    )
    ativo = models.BooleanField(default=True)
    data_adesao = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.inscricao} — {self.nome_titular}"


class SaldoPontos(models.Model):
    """Saldo acumulado de desconto no IPTU por imóvel no ciclo (ano)."""
    imovel = models.ForeignKey(Imovel, on_delete=models.PROTECT, related_name='saldos')
    ciclo = models.IntegerField(help_text='Ano de apuração')
    desconto_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Desconto acumulado no IPTU (%)')
    atualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('imovel', 'ciclo')

    def __str__(self):
        return (
            f"{self.imovel.inscricao} | {self.ciclo} | "
            f"{self.desconto_percentual}%"
        )