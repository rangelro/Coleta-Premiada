from django.db import models


class AuditLog(models.Model):
    OPERACAO_CHOICES = [
        ('INSERT', 'Insert'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('SELECT', 'Select'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    usuario_id = models.IntegerField(null=True, blank=True)
    usuario_email = models.CharField(max_length=255, null=True, blank=True)
    operacao = models.CharField(max_length=10, choices=OPERACAO_CHOICES)
    tabela = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=255, null=True, blank=True)
    dados_antes = models.JSONField(null=True, blank=True)
    dados_depois = models.JSONField(null=True, blank=True)
    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    endpoint = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp'], name='audit_log_timestamp_idx'),
            models.Index(fields=['usuario_id'], name='audit_log_usuario_id_idx'),
            models.Index(fields=['tabela'], name='audit_log_tabela_idx'),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.operacao} {self.tabela} (ID: {self.objeto_id}, User: {self.usuario_email})"
