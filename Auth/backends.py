from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import UCTabUsers

class UCTabUserBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            print(f'Tentando autenticar: {username}')
            user = UCTabUsers.objects.get(ucusername=username)
            

            if check_password(password, user.ucpassword):
                print("Usuario Logado")
                return user
                
            else:
                print('Senha incorreta.')
                return None
        except UCTabUsers.DoesNotExist:
            print('Usuário não encontrado.')
            return None

    def get_user(self, user_id):
        try:
            return UCTabUsers.objects.get(pk=user_id)
        except UCTabUsers.DoesNotExist:
            return None
