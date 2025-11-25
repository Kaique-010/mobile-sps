from django.db import connection
from django.contrib.auth.hashers import make_password
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from django.http import HttpRequest
from .models import Usuarios, Empresas, Filiais
from django.db.models import Max

def atualizar_senha(username, nova_senha, request=None):

    try:
        if request:
            banco = get_licenca_db_config(request) or 'default'
            if banco != "default":
                # Usar SQL direto para evitar problemas com tabelas de permissões
                from django.db import connections
                db_connection = connections[banco]
                with db_connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE usuarios SET usua_senh_mobi = %s WHERE usua_nome = %s",
                        [nova_senha, username]
                    )
                    if cursor.rowcount == 0:
                        raise Exception(f"Usuário {username} não encontrado no banco {banco}.")
                    print(f"Senha do usuário {username} atualizada com sucesso no banco {banco}.")
                    return True
        
        # Fallback para conexão padrão
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET usua_senh_mobi = %s WHERE usua_nome = %s",
                [nova_senha, username]
            )
            if cursor.rowcount == 0:
                raise Exception(f"Usuário {username} não encontrado.")
        print(f"Senha do usuário {username} atualizada com sucesso.")
        return True
    except Exception as e:
        print(f"Erro ao atualizar a senha do usuário {username}: {e}")
        raise e


def get_proximo_usuario(banco):
    """Gera próximo número de usuário"""
    maior = Usuarios.objects.using(banco).aggregate(Max('usua_codi'))['usua_codi__max'] or 0
    print(f"Maior usuário encontrado: {maior}")
    return maior + 1


def get_proxima_empresa(banco):
    """Gera próximo número de empresa"""
    maior = Empresas.objects.using(banco).aggregate(Max('empr_codi'))['empr_codi__max'] or 0
    print(f"Maior empresa encontrado: {maior}")
    return maior + 1

def get_proxima_filial(banco):
    """Gera próximo número de filial"""
    maior = Filiais.objects.using(banco).aggregate(Max('empr_codi'))['empr_codi__max'] or 0
    print(f"Maior filial encontrado: {maior}")
    return maior + 1

def get_proxima_filial_empr(banco):
    """Gera próximo número de filial"""
    maior = Filiais.objects.using(banco).aggregate(Max('empr_empr'))['empr_empr__max'] or 0
    print(f"Maior filial encontrado: {maior}")
    return maior + 1
