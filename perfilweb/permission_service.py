from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import PermissaoPerfil, PermissaoLog, PerfilHeranca, UsuarioPerfil
from .services import limpar_cache_perfil
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug
from django.core.cache import cache


@transaction.atomic
def salvar_permissoes(perfil, payload, operador=None):
    banco = get_db_from_slug(get_licenca_slug())
    PermissaoPerfil.objects.using(banco).filter(perf_perf=perfil).delete()

    permissoes = []
    logs = []
    for ct_id, acoes in payload.items():
        ct = ContentType.objects.using(banco).get(id=ct_id)
        for acao in acoes:
            pp = PermissaoPerfil(
                perf_perf=perfil,
                perf_ctype=ct,
                perf_acao=acao
            )
            permissoes.append(pp)
            logs.append(
                PermissaoLog(
                    perf_perf=perfil,
                    perf_ctype=ct,
                    perf_acao=acao,
                    perf_oper=getattr(operador, 'usuarios', None) if hasattr(operador, 'usuarios') else None,
                    perf_op='definir'
                )
            )

    if permissoes:
        PermissaoPerfil.objects.using(banco).bulk_create(permissoes)
    if logs:
        PermissaoLog.objects.using(banco).bulk_create(logs)
    limpar_cache_perfil(perfil.id)


@transaction.atomic
def salvar_herancas(perfil, pais_ids):
    banco = get_db_from_slug(get_licenca_slug())
    PerfilHeranca.objects.using(banco).filter(perf_filho=perfil).delete()
    objs = [PerfilHeranca(perf_filho=perfil, perf_pai_id=int(pid)) for pid in pais_ids if pid]
    if objs:
        PerfilHeranca.objects.using(banco).bulk_create(objs)
    limpar_cache_perfil(perfil.id)


@transaction.atomic
def salvar_usuarios_perfil(perfil, usuarios_ids):
    banco = get_db_from_slug(get_licenca_slug())
    # Normaliza IDs
    uids = [int(uid) for uid in usuarios_ids if uid]
    # Remover quaisquer vínculos existentes desses usuários com outros perfis
    if uids:
        UsuarioPerfil.objects.using(banco).filter(perf_usua_id__in=uids).delete()
    # Garantir que o perfil atual não tenha vínculos fora da lista (limpeza)
    UsuarioPerfil.objects.using(banco).filter(perf_perf=perfil).exclude(perf_usua_id__in=uids).delete()
    # Criar vínculos únicos (um perfil por usuário)
    objs = [UsuarioPerfil(perf_perf=perfil, perf_usua_id=uid, perf_ativ=True) for uid in uids]
    if objs:
        UsuarioPerfil.objects.using(banco).bulk_create(objs)
    for uid in uids:
        try:
            cache.delete(f'perfil_ativo_{banco}_{uid}')
        except Exception:
            pass
    limpar_cache_perfil(perfil.id)
