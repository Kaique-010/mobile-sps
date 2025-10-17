from django.urls import path
from .views import ParametrosViewSet

parametros_list = ParametrosViewSet.as_view({'get': 'configuracoes'})

urlpatterns = [
    path('parametros/configuracoes/', parametros_list, name='parametros-configuracoes'),
]
