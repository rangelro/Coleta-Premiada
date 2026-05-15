from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from auditlog.registry import auditlog


class Imovel(models.Model):
    """Unidade imobiliária participante"""
    MATERIAIS = [
        ('papel', 'Papel/Papelão'),
        ('plastico', 'Plástico'),
        ('aluminio', 'Alumínio'),
        ('vidro', 'Vidro'),
        ('metal', 'Metal'),
        ('eletronico', 'Eletrônico'),
    ]

    inscricao = models.CharField(max_length=50, unique=True)
    titular = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'perfil': 'morador'}, #limito a apenas usuarios com perfil 'morador'
        related_name='imoveis'
    )
    cep = models.CharField(max_length=9, help_text='Formato: XXXXX-XXX')
    logradouro = models.CharField(max_length=200)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2, help_text='Sigla do estado (UF)')
    num_moradores = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], help_text='Quantidade de moradores na residência')
    ativo = models.BooleanField(default=True)
    data_adesao = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.inscricao} — {self.titular.nome}"

auditlog.register(Imovel)

class SaldoPontos(models.Model):
    """Saldo acumulado de desconto no IPTU por imóvel no ciclo (mensal)."""
    imovel = models.ForeignKey(Imovel, on_delete=models.PROTECT, related_name='saldos')
    ciclo = models.CharField(max_length=7, help_text='Mês de apuração (MM-YYYY)')
    desconto_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Desconto acumulado no IPTU (%)')
    atualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('imovel', 'ciclo')

    def __str__(self):
        return (
            f"{self.imovel.inscricao} | {self.ciclo} | "
            f"{self.desconto_percentual}%"
        )
    
auditlog.register(SaldoPontos)