from django.db import connection
from django.contrib.auth.hashers import make_password

def atualizar_senha(self, nova_senha):
    """
    Atualiza a senha diretamente no banco SEM HASH, só pra testes.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET usua_senh_mobi = %s WHERE usua_nome = %s",
                [nova_senha, self.usua_nome]
            )
        print(f"Senha do usuário {self.usua_nome} atualizada sem hash.")
    except Exception as e:
        print(f"Erro ao atualizar a senha do usuário {self.usua_nome}: {e}")
