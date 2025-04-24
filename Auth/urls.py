from django.urls import path
from .views import (
    LoginView,
    EmpresaUsuarioView,
    FiliaisUsuarioView,
    SetEmpresaFilialView
)
from rest_framework_simplejwt.views import TokenRefreshView  

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('user-empresa/', EmpresaUsuarioView.as_view(), name='user-empresa'),  
    path('user-filiais/', FiliaisUsuarioView.as_view(), name='user-filiais'),    
    path('set-empresa-filial/', SetEmpresaFilialView.as_view(), name='set-empresa-filial'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
