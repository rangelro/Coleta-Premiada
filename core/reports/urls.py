from django.urls import path

from .views import GenerateReportView, ReportHistoryView

urlpatterns = [
    path('generate', GenerateReportView.as_view(), name='report-generate'),
    path('history',  ReportHistoryView.as_view(),  name='report-history'),
]
