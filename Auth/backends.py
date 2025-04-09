# Auth/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import UCTabUsers

class UCTabUserBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            print(f'\n[AUTH] Tentando autenticar: {username}')

            user = UCTabUsers.objects.get(ucusername=username)
            print(f'[AUTH] Usuário encontrado na UCTabUsers: {user.ucusername}')

            if check_password(password, user.ucpassword):
                print(f'[AUTH] Senha válida para: {username}')
                return user  # ← FALTAVA ISSO
            else:
                print('[AUTH] Senha incorreta.')
                return None

        except UCTabUsers.DoesNotExist:
            print('[AUTH] Usuário não encontrado na UCTabUsers.')
            return None

    def get_user(self, uciduser):
        try:
            return UCTabUsers.objects.get(id=uciduser)
        except UCTabUsers.DoesNotExist:
            return None
