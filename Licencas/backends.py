# Auth/backends.py
import datetime
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from .models import Licencas, Usuarios

class UserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, docu=None):
        try:
            print(f'\n[AUTH] Tentando autenticar: {username}')

            # Buscar o usuário pelo nome de usuário
            user = Usuarios.objects.get(usua_nome=username)
            print(f'[AUTH] Usuário encontrado: {user.usua_nome}')

            # Buscar a licença para o CNPJ
            licenca = Licencas.objects.filter(lice_docu=docu)
            if not licenca:
                print(f'[AUTH] Licença inválida ou bloqueada para o CNPJ {docu}.')
                return None

            # Verificar a data de expiração da licença
            if licenca._log_data and licenca._log_data < datetime.date.today():
                print(f'[AUTH] Licença expirada para o CNPJ {docu}.')
                return None

            if user.password == password:  # Se a senha estiver em texto simples, compará-la diretamente
                print(f'[AUTH] Senha válida para: {username}')
                return user 
            else:
                print(f'[AUTH] Senha fornecida: {password}')
                print(f'[AUTH] Senha no banco: {user.password}')
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
