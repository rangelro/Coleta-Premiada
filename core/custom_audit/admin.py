from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'operacao', 'tabela', 'objeto_id', 'usuario_email', 'ip_origem', 'endpoint')
    list_filter = ('operacao', 'tabela', 'timestamp')
    search_fields = ('usuario_email', 'objeto_id', 'endpoint', 'ip_origem')
    readonly_fields = ('timestamp', 'usuario_id', 'usuario_email', 'operacao', 'tabela', 'objeto_id', 'dados_antes', 'dados_depois', 'ip_origem', 'endpoint')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
