from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.db import IntegrityError, connections
from .constants import ACOES_PADRAO, PERFIS_PADRAO, DEFAULT_PERMISSOES_POR_PERFIL
from .models import Perfil, PermissaoPerfil, PerfilHeranca, UsuarioPerfil
from Licencas.models import Usuarios
from .services import limpar_cache_perfil, _buscar_contenttype
from core.middleware import get_licenca_slug
from core.utils import get_db_from_slug


def get_content_types_validos(banco=None):
    banco = banco or get_db_from_slug(get_licenca_slug())
    modelos = []
    for app_config in apps.get_app_configs():
        if app_config.name.startswith('django.'):
            continue
        
        # Obtém todos os modelos, incluindo managed=False (legados/views),
        # pois eles também precisam de controle de permissão.
        app_models = list(app_config.get_models())
        
        modelos.extend(app_models)
        print(f"Modelos do app {app_config.label}: {[m.__name__ for m in app_models]}") 
    
    try:
        cts = ContentType.objects.db_manager(banco).get_for_models(*modelos).values()
        return list(cts)
    except IntegrityError as e:
        # Corrige erro de coluna name NOT NULL em bancos antigos
        if 'null value in column "name"' in str(e):
            try:
                with connections[banco].cursor() as cursor:
                    cursor.execute('ALTER TABLE django_content_type ALTER COLUMN name DROP NOT NULL;')
                # Tenta novamente após correção
                cts = ContentType.objects.db_manager(banco).get_for_models(*modelos).values()
                return list(cts)
            except Exception:
                pass
        raise e


def listar_recursos():
    banco = get_db_from_slug(get_licenca_slug())
    recursos = []
    for ct in get_content_types_validos(banco=banco):
        recursos.append({
            'id': ct.id,
            'app_label': ct.app_label,
            'model': ct.model,
            'acoes': ACOES_PADRAO,
        })
    return recursos


def sincronizar_permissoes_padrao():
    banco = get_db_from_slug(get_licenca_slug())
    perfil = Perfil.objects.using(banco).filter(perf_nome='superadmin').first()
    if not perfil:
        return 0
    cts = get_content_types_validos(banco=banco)
    criados = 0
    for ct in cts:
        for acao in ACOES_PADRAO:
            obj, created = PermissaoPerfil.objects.using(banco).get_or_create(
                perf_perf=perfil,
                perf_ctype=ct,
                perf_acao=acao
            )
            if created:
                criados += 1
    limpar_cache_perfil(perfil.id)
    return criados


def criar_perfis_padrao():
    banco = get_db_from_slug(get_licenca_slug())
    criados = 0
    perfis = []
    for nome in PERFIS_PADRAO:
        perf, created = Perfil.objects.using(banco).get_or_create(perf_nome=nome, defaults={'perf_ativ': True})
        if created:
            criados += 1
        perfis.append(perf)
    return criados, perfis


def aplicar_permissoes_padrao_por_perfil(perfil):
    banco = get_db_from_slug(get_licenca_slug())
    regras = DEFAULT_PERMISSOES_POR_PERFIL.get(perfil.perf_nome, {})
    if not regras:
        return 0
    criados = 0
    from .services import _buscar_contenttype
    for (app_label, model), acoes in regras.items():
        ct, _ = _buscar_contenttype(banco, app_label, model)
        if not ct:
            continue
        for acao in acoes:
            _, created = PermissaoPerfil.objects.using(banco).get_or_create(
                perf_perf=perfil,
                perf_ctype=ct,
                perf_acao=acao
            )
            if created:
                criados += 1
    limpar_cache_perfil(perfil.id)
    return criados


def vincular_usuarios_padrao():
    banco = get_db_from_slug(get_licenca_slug())
    perf_super = Perfil.objects.using(banco).filter(perf_nome='superadmin').first()
    perf_assist = Perfil.objects.using(banco).filter(perf_nome='assistentes').first()
    if not perf_super or not perf_assist:
        return {'vinculos': 0}
    vinculos = 0
    for u in Usuarios.objects.using(banco).all():
        nome = (u.usua_nome or '').strip().lower()
        destino = perf_super if nome in ('admin', 'mobile') else perf_assist
        obj, created = UsuarioPerfil.objects.using(banco).get_or_create(
            perf_usua=u,
            perf_perf=destino,
            defaults={'perf_ativ': True}
        )
        if created:
            vinculos += 1
    return {'vinculos': vinculos}


def bootstrap_inicial():
    criados_count, perfis = criar_perfis_padrao()
    aplicados = 0
    for p in perfis:
        aplicados += aplicar_permissoes_padrao_por_perfil(p)
    vinc = vincular_usuarios_padrao()
    return {'perfis_criados': criados_count, 'permissoes_criadas': aplicados, **vinc}
