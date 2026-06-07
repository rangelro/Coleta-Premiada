from django.db import models
from django.conf import settings
from auditlog.registry import auditlog
from program.models import Imovel, Programa


class RegistroColeta(models.Model):
    """Coleta recebida da fila RabbitMQ e registrada no Core."""

    id_microservico = models.CharField(
        max_length=50, unique=True,
        help_text='ID gerado pelo microserviço (MongoDB)',
    )
    imovel = models.ForeignKey(Imovel, on_delete=models.PROTECT, related_name='coletas')
    programa = models.ForeignKey(
        Programa, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='coletas',
    )
    pontuacao = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text='Pontuação calculada no core: peso_kg × ConstantePontuacao.pontos_por_kg',
    )
    data_hora_coleta = models.DateTimeField(null=True, blank=True)
    peso_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0)

    class Meta:
        ordering = ['-id_microservico']

    def __str__(self):
        return f"{self.imovel.inscricao} | Pontuação: {self.pontuacao}"


class Evidencia(models.Model):
    """Evidência (foto/arquivo) anexada a uma coleta."""
    coleta = models.ForeignKey(RegistroColeta, on_delete=models.CASCADE, related_name='evidencias')
    descricao = models.CharField(max_length=255, blank=True)
    arquivo_url = models.URLField(help_text='URL do objeto no S3/MinIO')
    enviada_em = models.DateTimeField(auto_now_add=True)
    enviada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='evidencias_enviadas',
    )

    class Meta:
        ordering = ['-enviada_em']

    def __str__(self):
        return f"Evidência de {self.coleta} ({self.enviada_em:%d/%m/%Y})"


class Contestacao(models.Model):
    """Contestação aberta por um morador sobre uma coleta."""
    STATUS = [
        ('aberta', 'Aberta'),
        ('em_analise', 'Em análise'),
        ('aceita', 'Aceita'),
        ('negada', 'Negada'),
    ]

    coleta = models.ForeignKey(RegistroColeta, on_delete=models.PROTECT, related_name='contestacoes')
    aberta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='contestacoes_abertas',
        limit_choices_to={'perfil': 'morador'},
    )
    motivo = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS, default='aberta')
    analisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contestacoes_analisadas',
        limit_choices_to={'perfil': 'gestor'},
    )
    resposta = models.TextField(blank=True)
    aberta_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-aberta_em']

    def __str__(self):
        return f"Contestação #{self.id} ({self.status})"


auditlog.register(RegistroColeta)
auditlog.register(Evidencia)
auditlog.register(Contestacao)
