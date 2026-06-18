from django.urls import path
from .views import AuditLogListView, AuditLogExportView

urlpatterns = [
    # /logs
    path('logs',        AuditLogListView.as_view(),   name='audit-logs-list'),
    path('logs/export', AuditLogExportView.as_view(), name='audit-logs-export'),
]
