# Auth/backends.py
import datetime
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from .models import Licencas, UCTabUsers

class UCTabUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            print(f'\n[AUTH] Tentando autenticar: {username}')

            user = UCTabUsers.objects.get(ucusername=username)
            print(f'[AUTH] Usuário encontrado na UCTabUsers: {user.ucusername}')
            licenca = Licencas.objects.filter(lice_docu='lice_docu', lice_bloq=False).first()

            if not licenca:
                print(f'[AUTH] Licença inválida ou bloqueada para o CNPJ {licenca}.')
                return None  # Ou você pode lançar uma exceção personalizada

            # Se precisar, verifique a validade da licença (campo _log_data, por exemplo)
            if licenca._log_data and licenca._log_data < datetime.date.today():
                print(f'[AUTH] Licença do CNPJ {licenca} expirada.')
                return None  # Ou você pode lançar uma exceção personalizada

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
