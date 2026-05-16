from django.urls import path
from .views import ImovelCreateAPIView

urlpatterns = [
    path('adesao/', ImovelCreateAPIView.as_view(), name='adesao-morador'),
]
