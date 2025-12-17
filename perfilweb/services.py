from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from .models import UsuarioPerfil, PermissaoPerfil, Perfil, PerfilHeranca
from .permission_map import PERMISSION_MAP
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
import logging
from Licencas.models import Usuarios
from django.apps import apps

CACHE_TIMEOUT = 60  # Reduzir para 1 minuto durante debug
logger = logging.getLogger('perfilweb.services')

# Bancos/Licenças que não utilizam o sistema de perfis (permissão total/hardcoded)
EXCLUDED_DBS = ['savexml1', 'savexml206', 'spartacus', 'savexml144']


def get_perfil_ativo(usuario):
    """Retorna o perfil ativo do usuário"""
    if not usuario:
        logger.warning("[perfil_services] get_perfil_ativo: usuario None")
        return None
        
    banco = get_db_from_slug(get_licenca_slug())
    
    # EXCEÇÃO: Bancos específicos ignorados (sem perfil)
    if banco in EXCLUDED_DBS:
        return None

    usuario_id = getattr(usuario, 'usua_codi', None) or getattr(usuario, 'pk', None)
    
    if not usuario_id:
        logger.warning(f"[perfil_services] get_perfil_ativo: usuario_id None para usuario={usuario}")
        return None
    
    key = f'perfil_ativo_{banco}_{usuario_id}'
    perfil = cache.get(key)
    
    if perfil:
        logger.info(f"[perfil_services] perfil_ativo CACHE HIT: usuario_id={usuario_id} perfil={getattr(perfil,'perf_nome',None)}")
        return perfil

    rels = list(
        UsuarioPerfil.objects.using(banco)
        .select_related('perf_perf')
        .filter(perf_usua_id=usuario_id, perf_ativ=True, perf_perf__perf_ativ=True)
    )
    if not rels:
        cache.set(key, None, CACHE_TIMEOUT)
        logger.warning(f"[perfil_services] perfil_ativo NÃO ENCONTRADO: usuario_id={usuario_id} banco={banco}")
        return None
    melhor = None
    melhor_count = -1
    try:
        for rel in rels:
            p = rel.perf_perf
            cadeia = _cadeia_perfis(p)
            count = PermissaoPerfil.objects.using(banco).filter(perf_perf_id__in=cadeia).count()
            if count > melhor_count:
                melhor = p
                melhor_count = count
        if melhor is None:
            melhor = rels[0].perf_perf
    except Exception:
        melhor = rels[0].perf_perf
    # Enforce: manter apenas um perfil por usuário (remove duplicados)
    try:
        outros_ids = [rel.perf_perf_id for rel in rels if rel.perf_perf_id != melhor.id]
        if outros_ids:
            UsuarioPerfil.objects.using(banco).filter(perf_usua_id=usuario_id, perf_perf_id__in=outros_ids).delete()
    except Exception:
        pass
    cache.set(key, melhor, CACHE_TIMEOUT)
    logger.info(f"[perfil_services] perfil_ativo DB: usuario_id={usuario_id} banco={banco} perfil={melhor.perf_nome} perms_count={melhor_count}")
    return melhor


def _perfil_version(perfil_id):
    banco = get_db_from_slug(get_licenca_slug())
    key = f'perfil_ver_{banco}_{perfil_id}'
    ver = cache.get(key)
    if ver is None:
        ver = 1
        cache.set(key, ver, CACHE_TIMEOUT)
    return ver


def limpar_cache_perfil(perfil_id):
    """Limpa o cache de um perfil incrementando sua versão"""
    banco = get_db_from_slug(get_licenca_slug())
    key = f'perfil_ver_{banco}_{perfil_id}'
    ver = cache.get(key) or 1
    cache.set(key, ver + 1, CACHE_TIMEOUT)
    logger.info(f"[perfil_services] cache_limpo perfil_id={perfil_id} nova_versao={ver+1}")


def _cadeia_perfis(perfil):
    """Retorna a cadeia de herança de perfis (perfil + todos os pais)"""
    if not perfil:
        return []
    
    ids = [perfil.id]
    banco = get_db_from_slug(get_licenca_slug())
    pais = list(PerfilHeranca.objects.using(banco).filter(perf_filho=perfil).values_list('perf_pai_id', flat=True))
    visitados = set(ids)
    
    while pais:
        novo = []
        for pid in pais:
            if pid in visitados:
                continue
            ids.append(pid)
            visitados.add(pid)
            novo.extend(list(PerfilHeranca.objects.using(banco).filter(perf_filho_id=pid).values_list('perf_pai_id', flat=True)))
        pais = novo
    
    logger.info(f"[perfil_services] cadeia_perfis base={perfil.perf_nome} cadeia_ids={ids}")
    return ids


def _normalizar_app_label(app_label):
    """Normaliza app_label para lowercase e remove caracteres especiais"""
    return app_label.lower().replace('-', '_')


def _normalizar_model_name(model_name):
    """Normaliza model_name para lowercase"""
    return model_name.lower()


def _buscar_contenttype(banco, app_label, model_name):
    """
    Busca ContentType com múltiplas estratégias de fallback
    Retorna: (ContentType ou None, mensagem de debug)
    """
    app_norm = _normalizar_app_label(app_label)
    model_norm = _normalizar_model_name(model_name)
    
    logger.info(f"[perfil_services] _buscar_contenttype: app_original={app_label} model_original={model_name} app_norm={app_norm} model_norm={model_norm}")
    
    # Estratégia 1: Busca direta exata
    try:
        ct = ContentType.objects.using(banco).get(
            app_label__iexact=app_norm,
            model__iexact=model_norm
        )
        logger.info(f"[perfil_services] ContentType ENCONTRADO (direto): id={ct.id} app={ct.app_label} model={ct.model}")
        return ct, "busca_direta"
    except ContentType.DoesNotExist:
        logger.info(f"[perfil_services] ContentType não encontrado busca direta: app={app_norm} model={model_norm}")
    except Exception as e:
        logger.error(f"[perfil_services] Erro busca direta ContentType: {e}")
    
    # Estratégia 2: Buscar via apps.get_model com variações
    variações_model = [
        model_norm,
        model_norm.capitalize(),
        ''.join(word.capitalize() for word in model_norm.split('_')),
        model_name,  # Original
    ]
    
    for var_model in variações_model:
        try:
            model_cls = apps.get_model(app_norm, var_model)
            ct = ContentType.objects.db_manager(banco).get_for_model(model_cls, for_concrete_model=False)
            logger.info(f"[perfil_services] ContentType ENCONTRADO (get_model): id={ct.id} app={ct.app_label} model={ct.model} tentativa={var_model}")
            return ct, f"get_model_{var_model}"
        except Exception:
            pass
    
    # Estratégia 3: Buscar via AppConfig
    try:
        target_cfg = None
        for cfg in apps.get_app_configs():
            label = (cfg.label or '').lower()
            name = (cfg.name.split('.')[-1] or '').lower()
            if label == app_norm or name == app_norm:
                target_cfg = cfg
                break
        
        if target_cfg:
            logger.info(f"[perfil_services] AppConfig encontrada: {target_cfg.label}")
            for m in target_cfg.get_models():
                if m._meta.model_name.lower() == model_norm:
                    ct = ContentType.objects.db_manager(banco).get_for_model(m, for_concrete_model=False)
                    logger.info(f"[perfil_services] ContentType ENCONTRADO (AppConfig): id={ct.id} app={ct.app_label} model={ct.model}")
                    return ct, "appconfig"
    except Exception as e:
        logger.error(f"[perfil_services] Erro busca AppConfig: {e}")
    
    # Estratégia 4: Listar todos os ContentTypes disponíveis para debug
    try:
        todos_cts = ContentType.objects.using(banco).all().values('id', 'app_label', 'model')
        logger.warning(f"[perfil_services] ContentType NÃO ENCONTRADO. Disponíveis no banco: {list(todos_cts)[:20]}")
    except Exception:
        pass
    
    logger.error(f"[perfil_services] FALHA TOTAL: ContentType não encontrado para app={app_label} model={model_name}")
    return None, "not_found"

#Função que detecta as permissões de um perfil em um determinado app e modelo e conexão
def tem_permissao(perfil, app_label, model, acao):
    """
    Verifica se o perfil tem permissão para executar a ação no modelo
    """
    # EXCEÇÃO 1: Apps específicos (OrdemdeServico, O_S) ignorados
    app_norm = _normalizar_app_label(app_label)
    if app_norm in ['ordemdeservico', 'o_s', 'ordens', 'os', 'Produtos', 'produtos']:
        logger.info(f"[perfil_services] tem_permissao: app={app_label} EXCLUIDO DO CONTROLE DE PERFIL (permitido)")
        return True

    # EXCEÇÃO 2: Bancos específicos (savexml1, savexml206, spartacus) ignorados
    banco = get_db_from_slug(get_licenca_slug())
    if banco in EXCLUDED_DBS:
        logger.info(f"[perfil_services] tem_permissao: banco={banco} EXCLUIDO DO CONTROLE DE PERFIL (permitido)")
        return True

    if not perfil:
        logger.warning(f"[perfil_services] tem_permissao: perfil None para app={app_label} model={model} acao={acao}")
        return False

    cadeia = _cadeia_perfis(perfil)
    ver = _perfil_version(perfil.id)
    # banco já foi obtido acima
    
    # Normalizar antes de criar a chave de cache
    model_norm = _normalizar_model_name(model)
    
    key = f'perm_{banco}_{perfil.id}_v{ver}_{",".join(map(str,cadeia))}_{app_norm}_{model_norm}_{acao}'
    permitido = cache.get(key)
    
    if permitido is not None:
        logger.info(f"[perfil_services] tem_permissao CACHE: perfil={perfil.perf_nome} app={app_norm} model={model_norm} acao={acao} permitido={permitido}")
        return permitido

    logger.info(f"[perfil_services] tem_permissao VERIFICANDO: perfil={perfil.perf_nome} app={app_label}→{app_norm} model={model}→{model_norm} acao={acao} cadeia={cadeia}")
    
    ct, estrategia = _buscar_contenttype(banco, app_label, model)
    
    if not ct:
        # NÃO fazer cache de False aqui! Pode ser problema temporário
        logger.error(f"[perfil_services] tem_permissao NEGADO (ContentType não encontrado): perfil={perfil.perf_nome} app={app_label} model={model}")
        return False

    # Verificar se existe a permissão
    permitido = PermissaoPerfil.objects.using(banco).filter(
        perf_perf_id__in=cadeia,
        perf_ctype=ct,
        perf_acao=acao
    ).exists()

    cache.set(key, permitido, CACHE_TIMEOUT)
    
    logger.info(f"[perfil_services] tem_permissao RESULTADO: perfil={perfil.perf_nome} app={app_norm} model={model_norm} ct_id={ct.id} acao={acao} permitido={permitido} estrategia={estrategia}")
    
    # Se negado, listar o que o perfil TEM para este ContentType
    if not permitido:
        acoes_disponiveis = list(PermissaoPerfil.objects.using(banco).filter(
            perf_perf_id__in=cadeia,
            perf_ctype=ct
        ).values_list('perf_acao', flat=True))
        logger.warning(f"[perfil_services] ACESSO NEGADO: perfil={perfil.perf_nome} solicitou acao={acao} mas tem apenas: {acoes_disponiveis}")
    
    return permitido


def acoes_permitidas(perfil, app_label, model):
    """Retorna conjunto de ações permitidas para o modelo"""
    # EXCEÇÃO 1: Apps específicos
    app_norm = _normalizar_app_label(app_label)
    if app_norm in ['ordemdeservico', 'o_s', 'ordens', 'os', 'Produtos', 'produtos']:
        logger.info(f"[perfil_services] acoes_permitidas: app={app_label} EXCLUIDO DO CONTROLE DE PERFIL (todas permitidas)")
        return {'criar', 'editar', 'excluir', 'visualizar', 'listar', 'imprimir', 'exportar'}

    # EXCEÇÃO 2: Bancos específicos
    banco = get_db_from_slug(get_licenca_slug())
    if banco in EXCLUDED_DBS:
        logger.info(f"[perfil_services] acoes_permitidas: banco={banco} EXCLUIDO DO CONTROLE DE PERFIL (todas permitidas)")
        return {'criar', 'editar', 'excluir', 'visualizar', 'listar', 'imprimir', 'exportar'}

    if not perfil:
        return set()
    
    model_norm = _normalizar_model_name(model)
    
    ct, estrategia = _buscar_contenttype(banco, app_label, model)
    
    if not ct:
        logger.error(f"[perfil_services] acoes_permitidas: ContentType não encontrado app={app_label} model={model}")
        return set()
    
    cadeia = _cadeia_perfis(perfil)
    acoes = set(PermissaoPerfil.objects.using(banco).filter(
        perf_perf_id__in=cadeia,
        perf_ctype=ct
    ).values_list('perf_acao', flat=True))
    
    logger.info(f"[perfil_services] acoes_permitidas: perfil={perfil.perf_nome} app={app_norm} model={model_norm} acoes={sorted(acoes)}")
    return acoes


def listar_permissoes(perfil):
    """Lista todas as permissões do perfil (incluindo herança)"""
    if not perfil:
        return []
    
    banco = get_db_from_slug(get_licenca_slug())
    cadeia = _cadeia_perfis(perfil)
    qs = PermissaoPerfil.objects.using(banco).filter(perf_perf_id__in=cadeia)
    
    cids = list(qs.values_list('perf_ctype_id', flat=True))
    ct_map = {
        cid: (rec['app_label'], rec['model'])
        for rec in ContentType.objects.using(banco).filter(id__in=set(cids)).values('id', 'app_label', 'model')
        for cid in [rec['id']]
    }
    
    items = []
    for cid, acao in qs.values_list('perf_ctype_id', 'perf_acao'):
        app_model = ct_map.get(cid)
        if app_model:
            items.append({'app': app_model[0], 'model': app_model[1], 'acao': acao})
    
    logger.info(f"[perfil_services] listar_permissoes: perfil={perfil.perf_nome} total={len(items)} primeiras_10={items[:10]}")
    return items


def verificar_por_url(usuario, url_name):
    """Verifica permissão baseada no nome da URL"""
    # EXCEÇÃO PRELIMINAR: Banco específico
    banco = get_db_from_slug(get_licenca_slug())
    if banco in ['savexml1', 'savexml206', 'savexml144']:
         logger.info(f"[perfil_services] verificar_por_url: banco={banco} EXCLUIDO DO CONTROLE DE PERFIL (permitido)")
         return True

    perfil = get_perfil_ativo(usuario)
    regra = PERMISSION_MAP.get(url_name)
    
    if not regra:
        logger.info(f"[perfil_services] verificar_por_url: url_name={url_name} SEM REGRA (permitido)")
        return True
    
    app_label, model, acao = regra
    
    # EXCEÇÃO TOTAL na verificação por URL também, para garantir
    app_norm = _normalizar_app_label(app_label)
    if app_norm in ['ordemdeservico', 'o_s', 'ordens', 'os', 'Produtos', 'produtos']:
        logger.info(f"[perfil_services] verificar_por_url: app={app_label} EXCLUIDO DO CONTROLE DE PERFIL (permitido)")
        return True

    resultado = tem_permissao(perfil, app_label, model, acao)
    
    logger.info(f"[perfil_services] verificar_por_url: url_name={url_name} regra=({app_label}, {model}, {acao}) resultado={resultado}")
    return resultado


def auditar_permissoes_usuarios():
    """Audita permissões de todos os usuários (para debug)"""
    banco = get_db_from_slug(get_licenca_slug())
    if banco in EXCLUDED_DBS:
        return
    
    try:
        todos = list(Usuarios.objects.using(banco).all())
    except Exception as e:
        logger.warning(f"[perfil_services] audit falha listar usuarios banco={banco} err={e}")
        return
    
    for u in todos:
        try:
            uid = getattr(u, 'usua_codi', None)
            nome = (getattr(u, 'usua_nome', '') or '').strip()
            
            rels = list(UsuarioPerfil.objects.using(banco).filter(
                perf_usua_id=uid, 
                perf_ativ=True
            ).select_related('perf_perf'))
            
            perfis = [r.perf_perf for r in rels if getattr(r, 'perf_perf', None)]
            
            if not perfis:
                logger.info(f"[perfil_services] audit: usuario={nome} SEM PERFIL ATIVO")
                continue
            
            cadeia = []
            for p in perfis:
                cadeia.extend(_cadeia_perfis(p))
            cadeia = list(sorted(set(cadeia)))
            
            qs = PermissaoPerfil.objects.using(banco).filter(perf_perf_id__in=cadeia)
            total_perms = qs.count()
            
            cids = list(qs.values_list('perf_ctype_id', flat=True))
            ct_map = {
                cid: (rec['app_label'], rec['model'])
                for rec in ContentType.objects.using(banco).filter(id__in=set(cids)).values('id', 'app_label', 'model')
                for cid in [rec['id']]
            }
            
            perms = {}
            for cid, acao in qs.values_list('perf_ctype_id', 'perf_acao'):
                app_model = ct_map.get(cid)
                if not app_model:
                    continue
                k = f"{app_model[0]}.{app_model[1]}"
                perms.setdefault(k, set()).add(acao)
            
            resumo = {k: sorted(list(v)) for k, v in perms.items()}
            
            logger.info(f"[perfil_services] audit: usuario={nome} perfis={[p.perf_nome for p in perfis]} total_permissoes={total_perms} recursos={len(resumo)} sample={list(resumo.items())[:5]}")
            
        except Exception as e:
            logger.warning(f"[perfil_services] audit usuario_err: err={e}")
