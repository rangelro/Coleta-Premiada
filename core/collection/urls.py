from django.urls import path
from .views import (
    ColetaListCreateView, ColetaDetailView,
    EvidenciaListCreateView,
    ContestacaoListCreateView, ContestacaoDetailView,
)

urlpatterns = [
    # /collections
    path('collections',                ColetaListCreateView.as_view(), name='coleta-list-create'),
    path('collections/<int:pk>',       ColetaDetailView.as_view(),     name='coleta-detail'),
    path('collections/<int:id>/evidences',
         EvidenciaListCreateView.as_view(), name='coleta-evidences'),

    # /disputes
    path('disputes',                   ContestacaoListCreateView.as_view(), name='dispute-list-create'),
    path('disputes/<int:pk>',          ContestacaoDetailView.as_view(),     name='dispute-detail'),
]
