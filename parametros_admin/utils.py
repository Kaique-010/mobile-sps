from django.core.cache import cache
from pprint import pprint
from django.utils import timezone
from parametros_admin.models import Modulo, PermissaoModulo
from core.registry import get_licenca_db_config
import logging
import json
from Licencas.models import Empresas, Filiais
from .models import PermissaoModulo

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
        # Adicionar debug temporário
        debug_modulo_pisos(banco, empresa_id, filial_id)
        
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


def debug_modulo_pisos(banco, empresa_id=1, filial_id=1):
    """
    Função de debug para verificar o status do módulo Pisos
    """
    try:
        from .models import Modulo, PermissaoModulo
        
        
        # Verificar se o módulo Pisos existe
        try:
            modulo_pisos = Modulo.objects.using(banco).get(modu_nome='Pisos')
        
          
        except Modulo.DoesNotExist:
            print("✗ Módulo Pisos NÃO encontrado na tabela modulosmobile")
            return
        
        # Verificar permissões
        try:
            permissao = PermissaoModulo.objects.using(banco).get(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_modu=modulo_pisos
            )
      
        except PermissaoModulo.DoesNotExist:
            print(f"✗ Permissão NÃO encontrada para empresa {empresa_id}/filial {filial_id}")
            
       
            
    except Exception as e:
        print(f"Erro no debug: {e}")
        logger.error(f"Erro no debug do módulo Pisos: {e}")


def get_empresas_usuario(usuario_id, banco):
    """Retorna empresas que o usuário tem acesso"""
    cache_key = f"empresas_usuario_{usuario_id}_{banco}"
    empresas = cache.get(cache_key)
    
    if empresas is None:
        # Implementar lógica de negócio para determinar empresas do usuário
        # Por enquanto, retorna todas
        empresas_qs = Empresas.objects.using(banco).all()
        empresas = []
        
        for empresa in empresas_qs:
            filiais = Filiais.objects.using(banco).filter(empr_codi=empresa.empr_codi)
            
            for filial in filiais:
                empresas.append({
                    'empresa_id': empresa.empr_codi,
                    'empresa_nome': empresa.empr_nome,
                    'filial_id': filial.empr_empr,
                    'filial_nome': filial.empr_nome
                })
        
        cache.set(cache_key, empresas, 300)  # Cache por 5 minutos
    
    return empresas

def verificar_permissao_modulo(usuario_id, empresa_id, filial_id, modulo_nome, banco):
    """Verifica se usuário tem permissão para módulo específico"""
    try:
        from .models import Modulo
        
        modulo = Modulo.objects.using(banco).get(modu_nome=modulo_nome)
        
        permissao = PermissaoModulo.objects.using(banco).get(
            perm_empr=empresa_id,
            perm_fili=filial_id,
            perm_modu=modulo
        )
        
        return permissao.perm_ativ and not permissao.is_vencido
        
    except (Modulo.DoesNotExist, PermissaoModulo.DoesNotExist):
        return False

def limpar_cache_permissoes(empresa_id=None, filial_id=None):
    """Limpa cache de permissões"""
    if empresa_id and filial_id:
        cache_pattern = f"*empresa_{empresa_id}_filial_{filial_id}*"
    else:
        cache_pattern = "*empresas_usuario_*"
    
    # Implementar limpeza de cache baseada no padrão
    cache.clear()




