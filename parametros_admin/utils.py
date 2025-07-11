from django.core.cache import cache
from pprint import pprint
from django.utils import timezone
from parametros_admin.models import Modulo, PermissaoModulo
from core.registry import get_licenca_db_config
import logging
import json

logger = logging.getLogger(__name__)


def get_modulo_by_name(nome_modulo, banco=None):
    """
    Busca um módulo pelo nome
    """
    try:
        from .models import Modulo
        if banco:
            return Modulo.objects.using(banco).get(modu_nome=nome_modulo, modu_ativ=True)
        else:
            return Modulo.objects.get(modu_nome=nome_modulo, modu_ativ=True)
    except Modulo.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar módulo {nome_modulo}: {e}")
        return None



def get_modulos_globais(banco):
    from parametros_admin.models import Modulo
    
    queryset = Modulo.objects.using(banco).filter(
        modu_ativ=True
    ).values(
        'modu_codi', 'modu_nome', 'modu_desc', 'modu_icon', 'modu_orde', 'modu_ativ'
    ).order_by('modu_orde', 'modu_nome')
    
    return list(queryset)


def get_codigos_modulos_liberados(banco, empresa_id, filial_id):
    from parametros_admin.models import PermissaoModulo
    
    # Buscar permissões ativas para a empresa/filial
    permissoes = PermissaoModulo.objects.using(banco).filter(
        perm_empr=empresa_id, 
        perm_fili=filial_id, 
        perm_ativ=True
    ).select_related('perm_modu')
    
    # Extrair os códigos dos módulos ativos
    codigos_liberados = []
    for permissao in permissoes:
        if permissao.perm_modu and permissao.perm_modu.modu_ativ:
            codigos_liberados.append(permissao.perm_modu.modu_codi)
    
    return codigos_liberados




def get_modulos_liberados_empresa(banco, empresa_id, filial_id):
    """
    Busca módulos liberados para uma empresa/filial específica no banco de dados
    """
    try:
        from .models import PermissaoModulo
        
        # Buscar permissões ativas para a empresa/filial
        permissoes = PermissaoModulo.objects.using(banco).filter(
            perm_empr=empresa_id,
            perm_fili=filial_id,
            perm_ativ=True
        ).select_related('perm_modu')
        
        # Retornar lista de nomes dos módulos liberados
        modulos_liberados = []
        for permissao in permissoes:
            if permissao.perm_modu.modu_ativ:  # Verificar se o módulo está ativo
                modulos_liberados.append(permissao.perm_modu.modu_nome)
        
        return modulos_liberados
        
    except Exception as e:
        logger.error(f"Erro ao buscar módulos liberados para empresa {empresa_id}/filial {filial_id}: {e}")
        return []




