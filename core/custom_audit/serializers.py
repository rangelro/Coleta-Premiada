from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'usuario_id', 'usuario_email', 'operacao',
            'tabela', 'objeto_id', 'dados_antes', 'dados_depois',
            'ip_origem', 'endpoint', 'cidade',
        ]
        read_only_fields = fields
