from django.db import models
from django.conf import settings
from program.models import Imovel, Programa


class RegistroColeta(models.Model):
    """Coleta recebida da fila RabbitMQ e registrada no Core."""

    id_microservico = models.CharField(
        max_length=50, unique=True, null=True, blank=True,
        help_text='ID gerado pelo microserviço (MongoDB). Nulo para coletas manuais.',
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
    foto_url = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Caminho relativo do objeto no MinIO (ex: evidencias/uuid.jpg). '
                  'O frontend monta a URL do proxy a partir deste path.',
    )
    ciclo_consolidado = models.ForeignKey(
        'program.Ciclo', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='coletas_consolidadas',
        help_text='Ciclo no qual esta coleta foi convertida em benefícios'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='coletas_registradas',
        help_text='Usuário (Gestor/Supervisor) que registrou a coleta manualmente. Nulo se veio do app.'
    )

    class Meta:
        ordering = ['-id_microservico']

    def __str__(self):
        return f"{self.imovel.inscricao} | Pontuação: {self.pontuacao}"


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
