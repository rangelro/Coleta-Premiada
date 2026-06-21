from django.conf import settings
from django.db import models


class RelatorioLLM(models.Model):
    TIPOS = [
        ('participacao', 'Participação'),
        ('impacto', 'Impacto'),
        ('ranking', 'Ranking'),
        ('auditoria', 'Auditoria'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPOS)
    periodo_inicio = models.DateField()
    periodo_fim = models.DateField()
    programa = models.ForeignKey(
        'program.Programa',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='relatorios_llm',
    )
    relatorio = models.TextField()
    tokens_utilizados = models.PositiveIntegerField(default=0)
    gerado_em = models.DateTimeField(auto_now_add=True)
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='relatorios_llm_gerados',
    )

    class Meta:
        ordering = ['-gerado_em']

    def __str__(self):
        return f"Relatório {self.tipo} ({self.gerado_em:%d/%m/%Y})"
