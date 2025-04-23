from django.urls import path
from .views import LoginView, EmpresasDoUsuarioView, FiliaisDaEmpresaView, EmpresaListView, FilialListView, SetEmpresaFilialView
from rest_framework_simplejwt.views import TokenRefreshView  

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('empresas/', EmpresaListView.as_view(), name='empresa-list'), 
    path('filiais/', FilialListView.as_view(), name='filial-list'),   
    path('user-empresas/', EmpresasDoUsuarioView.as_view(), name='user-empresas'),  
    path('user-filiais/', FiliaisDaEmpresaView.as_view(), name='user-filiais'),    
    path('set-empresa-filial/', SetEmpresaFilialView.as_view(), name='set-empresa-filial'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
