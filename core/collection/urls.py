from django.urls import path
from .views import (
    ColetaListCreateView, ColetaDetailView,
    ImageProxyView,
    ContestacaoListCreateView, ContestacaoDetailView,
)

urlpatterns = [
    # /collections
    path('collections',                ColetaListCreateView.as_view(), name='coleta-list-create'),
    path('collections/<int:pk>',       ColetaDetailView.as_view(),     name='coleta-detail'),
    path('collections/images/',        ImageProxyView.as_view(),       name='image-proxy'),

    # /disputes
    path('disputes',                   ContestacaoListCreateView.as_view(), name='dispute-list-create'),
    path('disputes/<int:pk>',          ContestacaoDetailView.as_view(),     name='dispute-detail'),
]
