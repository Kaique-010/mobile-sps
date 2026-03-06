from django.urls import path
from .Views import AuditoriaListView

urlpatterns = [
    path('', AuditoriaListView.as_view(), name='auditoria_list'),
]