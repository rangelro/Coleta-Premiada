from django.urls import path

from .views import GenerateReportView, ReportDetailView, ReportHistoryView

urlpatterns = [
    path('generate', GenerateReportView.as_view(), name='report-generate'),
    path('history',  ReportHistoryView.as_view(),  name='report-history'),
    path('<int:pk>', ReportDetailView.as_view(),   name='report-detail'),
]
