from django.urls import path
from .views import RegistrarPesagemView

urlpatterns = [
    path('pesagens/', RegistrarPesagemView.as_view(), name='registrar-pesagem'),
]