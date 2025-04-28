# Auth/backends.py
import datetime
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from .models import Licencas, Usuarios

class UserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, docu=None):
        try:
            print(f'\n[AUTH] Tentando autenticar: {username}')

            user = Usuarios.objects.get(usua_nome=username)
            print(f'[AUTH] Usuário encontrado: {user.usua_nome}')

            licenca = Licencas.objects.filter(lice_docu=docu, lice_bloq=False).first()
            if not licenca:
                print(f'[AUTH] Licença inválida ou bloqueada para o CNPJ {docu}.')
                return None

            if licenca._log_data and licenca._log_data < datetime.date.today():
                print(f'[AUTH] Licença expirada para o CNPJ {docu}.')
                return None

            if check_password(password, user.usua_senh_mobi):
                print(f'[AUTH] Senha válida para: {username}')
                return user 
            else:
                print('[AUTH] Senha incorreta.')
                return None

        except Usuarios.DoesNotExist:
            print('[AUTH] Usuário não encontrado.')
            return None

    def get_user(self, usua_codi):
        try:
            return Usuarios.objects.get(usua_codi=usua_codi)
        except Usuarios.DoesNotExist:
            return None
