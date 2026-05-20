from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from auditlog.registry import auditlog


class Programa(models.Model):
    """Programa Coleta Premiada de um ciclo (geralmente um ano)."""
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    ativo = models.BooleanField(default=True)
    desconto_maximo = models.DecimalField(
        max_digits=5, decimal_places=2, default=40.00,
        help_text='Teto de desconto no IPTU por ciclo (em %)',
    )

    class Meta:
        ordering = ['-data_inicio']

    def __str__(self):
        return f"{self.nome} ({self.data_inicio:%Y})"



class RegraPrograma(models.Model):
    """Regras configuráveis (chave/valor) associadas a um Programa."""
    programa = models.OneToOneField(Programa, on_delete=models.CASCADE, related_name='regras')
    pontos_por_real = models.DecimalField(
        max_digits=6, decimal_places=2, default=10.00,
        help_text='Quantos pontos equivalem a 1% de desconto',
    )
    minimo_para_beneficio = models.PositiveIntegerField(
        default=100,
        help_text='Pontuação mínima para gerar qualquer benefício',
    )
    permite_acumulo_ciclos = models.BooleanField(default=False)

    def __str__(self):
        return f"Regras de {self.programa}"


class Imovel(models.Model):
    """Unidade imobiliária participante."""
    inscricao = models.CharField(max_length=50, unique=True)
    titular = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        limit_choices_to={'perfil': 'morador'},
        related_name='imoveis',
    )
    moradores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='imoveis_vinculados',
        help_text='Demais usuários (moradores) vinculados ao imóvel',
    )
    cep = models.CharField(max_length=9, help_text='Formato: XXXXX-XXX')
    logradouro = models.CharField(max_length=200)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2, help_text='Sigla do estado (UF)')
    num_moradores = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    ativo = models.BooleanField(default=True)
    data_adesao = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.inscricao} — {self.titular.nome}"


class SaldoPontos(models.Model):
    """Saldo acumulado de desconto no IPTU por imóvel no ciclo (mensal)."""
    imovel = models.ForeignKey(Imovel, on_delete=models.PROTECT, related_name='saldos')
    programa = models.ForeignKey(
        Programa, on_delete=models.PROTECT, related_name='saldos', null=True, blank=True,
    )
    ciclo = models.CharField(max_length=7, help_text='Mês de apuração (MM-YYYY)')
    desconto_percentual = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Desconto acumulado no IPTU (%)',
    )
    atualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('imovel', 'programa', 'ciclo')

    def __str__(self):
        return f"{self.imovel.inscricao} | {self.ciclo} | {self.desconto_percentual}%"


class Consolidacao(models.Model):
    """
    Processo de fechamento do ciclo do Programa: agrega os pontos
    e converte em benefícios (desconto no IPTU).
    """
    STATUS = [
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('concluida', 'Concluída'),
        ('falhou', 'Falhou'),
    ]

    programa = models.ForeignKey(Programa, on_delete=models.PROTECT, related_name='consolidacoes')
    executada_em = models.DateTimeField(auto_now_add=True)
    executada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='consolidacoes_executadas',
    )
    status = models.CharField(max_length=20, choices=STATUS, default='pendente')
    total_imoveis = models.PositiveIntegerField(default=0)
    total_pontos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ['-executada_em']

    def __str__(self):
        return f"Consolidação {self.programa.nome} ({self.status})"


class ConstantePontuacao(models.Model):
    """
    Singleton que define quantos pontos cada kg de material reciclável gera.
    Editável apenas por supervisor via API.
    """
    pontos_por_kg = models.DecimalField(
        max_digits=8, decimal_places=4, default='1.5000',
        help_text='Pontos gerados por kg coletado (peso × constante = pontuação)',
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='constantes_pontuacao_atualizadas',
    )

    class Meta:
        verbose_name = 'constante de pontuação'
        verbose_name_plural = 'constante de pontuação'

    def __str__(self):
        return f"{self.pontos_por_kg} pts/kg"

    @classmethod
    def get_valor(cls) -> 'ConstantePontuacao':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


auditlog.register(Programa)
auditlog.register(RegraPrograma)
auditlog.register(Imovel)
auditlog.register(SaldoPontos)
auditlog.register(Consolidacao)
auditlog.register(ConstantePontuacao)
