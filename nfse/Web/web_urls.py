from django.urls import path
from nfse.Web.Views.criar import NfseCreateView
from nfse.Web.Views.list import NfseListView
from nfse.Web.Views.deletar import NfseDeleteView
from nfse.Web.Views.consultar import NfseConsultarView
from nfse.Web.Views.cancelar import NfseCancelarView



app_name = 'nfse_web'

urlpatterns = [
    path('<slug:slug>/nfse/', NfseListView.as_view(), name='list'),
    path('<slug:slug>/nfse/novo/', NfseCreateView.as_view(), name='criar'),
    path('<slug:slug>/nfse/<int:pk>/deletar/', NfseDeleteView.as_view(), name='deletar'),
    path('<slug:slug>/nfse/<int:pk>/consultar/', NfseConsultarView.as_view(), name='consultar'),
    path('<slug:slug>/nfse/<int:pk>/cancelar/', NfseCancelarView.as_view(), name='cancelar'),
]