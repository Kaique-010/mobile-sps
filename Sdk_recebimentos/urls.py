from django.urls import path
from .views import RegistrarRecebimentoView

urlpatterns = [
    path('registrar/', RegistrarRecebimentoView.as_view()),
]

app_name = 'Sdk_recebimentos'