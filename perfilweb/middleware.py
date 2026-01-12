from django.http import HttpResponseForbidden
from django.urls import resolve
from .services import verificar_por_url
from .permission_map import PERMISSION_MAP
from .services import tem_permissao, get_perfil_ativo, acoes_permitidas, listar_permissoes, normalizar_app_label
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
import logging
from core.middleware import get_licenca_slug
from core.middleware import set_licenca_slug
from core.utils import get_db_from_slug
from django.conf import settings
from Licencas.models import Usuarios
import jwt
from core.licenca_context import get_licencas_map
from django.contrib import messages
from django.shortcuts import redirect


class PerfilPermissionMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('perfilweb.middleware')

    def __call__(self, request):
        usuario = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        p = request.path or ""
        try:
            parts_init = p.strip('/').split('/')
            slug_res = None
            if len(parts_init) >= 2 and parts_init[0] == 'web':
                if parts_init[1] == 'home':
                    if len(parts_init) >= 3 and parts_init[2] != 'selecionar-empresa':
                        cand = (parts_init[2] or '').strip().lower()
                        if any((x.get('slug') or '').strip().lower() == cand for x in get_licencas_map()):
                            slug_res = cand
                else:
                    # Somente considera slug quando há um app após o slug
                    if len(parts_init) >= 3:
                            cand = (parts_init[1] or '').strip().lower()
                            if any((x.get('slug') or '').strip().lower() == cand for x in get_licencas_map()):
                                slug_res = cand
            elif len(parts_init) >= 2 and parts_init[0] == 'api':
                cand = (parts_init[1] or '').strip().lower()
                if cand in ('null', 'undefined'):
                    slug_res = None
                else:
                    if any((x.get('slug') or '').strip().lower() == cand for x in get_licencas_map()):
                        slug_res = cand
                    else:
                        slug_res = None
            if not slug_res:
                try:
                    auth = request.headers.get('Authorization', '')
                    if auth.startswith('Bearer '):
                        token = auth.split(' ')[1]
                        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                        slug_res = claims.get('lice_slug') or slug_res
                except Exception:
                    pass
            if slug_res:
                try:
                    set_licenca_slug(slug_res)
                except Exception:
                    pass
        except Exception:
            pass

        if p.startswith('/api/licencas/mapa/') or '/api/selecionar-empresa/' in p or '/api/entidades-login/' in p:
            return self.get_response(request)
        
        # Ignorar rota de login de entidades com slug
        parts = p.strip('/').split('/')
        if len(parts) >= 4 and parts[2] == 'entidades' and parts[3] == 'login':
            return self.get_response(request)

        if '/parametros-admin/' in p or '/notificacoes/' in p:
            return self.get_response(request)
        if p.startswith('/api/schema/') or p.startswith('/api/schemas/') or p.startswith('/api/swagger'):
            return self.get_response(request)
        if p.startswith('/api/'):
            parts = p.strip('/').split('/')
            if len(parts) >= 3 and parts[2] in ('licencas', 'auth'):
                return self.get_response(request)
        if p.startswith('/web/'):
            parts = p.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'web' and parts[1] == 'home' and parts[2] == 'selecionar-empresa':
                return self.get_response(request)
            if p.startswith('/web/login/'):
                return self.get_response(request)
        if p.startswith('/static/') or p.startswith('/media/'):
            return self.get_response(request)

        if not usuario and request.path.startswith('/api/'):
            auth = request.headers.get('Authorization', '')
            if auth.startswith('Bearer '):
                try:
                    token = auth.split(' ')[1]
                    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    uid = claims.get('usuario_id') or claims.get('user_id')
                    try:
                        uid = int(uid) if uid is not None else None
                    except Exception:
                        uid = None
                    uname = claims.get('username') or claims.get('usua_nome')
                    slug_claim = claims.get('lice_slug')
                    slug_ctx = None
                    banco_ctx = None
                    try:
                        slug_ctx = get_licenca_slug() or slug_claim
                        banco_ctx = get_db_from_slug(slug_ctx)
                    except Exception:
                        slug_ctx = slug_claim
                        banco_ctx = get_db_from_slug(slug_ctx) if slug_ctx else None
                    try:
                        if slug_ctx:
                            set_licenca_slug(slug_ctx)
                        self.logger.info(f"[perfil_mw] jwt uid={uid} uname={uname} slug={slug_ctx} banco={banco_ctx}")
                    except Exception:
                        pass
                    if banco_ctx:
                        if uid:
                            usuario = Usuarios.objects.using(banco_ctx).filter(usua_codi=uid).first()
                        if not usuario and uname:
                            usuario = Usuarios.objects.using(banco_ctx).filter(usua_nome__iexact=uname).first()
                        try:
                            self.logger.info(f"[perfil_mw] jwt usuario_resolvido={getattr(usuario,'usua_nome',None)}")
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        self.logger.warning(f"[perfil_mw] jwt_decode_error={e}")
                    except Exception:
                        pass

        # Prosseguir mesmo sem usuário para negar acesso a rotas protegidas (exceto whitelists acima)

        try:
            perfil_snap = get_perfil_ativo(usuario)
            self.logger.info(f"[perfil_mw] perfil_resolvido={getattr(perfil_snap,'perf_nome',None)} usuario={getattr(usuario,'usua_nome',None)}")
            try:
                listar_permissoes(perfil_snap)
            except Exception:
                pass
        except Exception:
            pass

        try:
            slug = get_licenca_slug()
            banco = get_db_from_slug(slug)
            mods = getattr(request, 'modulos_disponiveis', [])
            self.logger.info(f"[perfil_mw] path={request.path} user={getattr(usuario,'usua_nome',None)} slug={slug} banco={banco} mods={mods}")
            try:
                from django.core.cache import cache
                from django.conf import settings as dj_settings
                if dj_settings.DEBUG:
                    tk = f"audit_perms_{banco}"
                    if cache.get(tk) is None:
                        cache.set(tk, 1, 30)
                        try:
                            from .services import auditar_permissoes_usuarios
                            auditar_permissoes_usuarios(banco)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

        try:
            match = resolve(request.path_info)
        except Exception as e:
            try:
                self.logger.warning(f"[perfil_mw] resolve_error path={request.path_info} err={e}")
            except Exception:
                pass
            match = None
        view_func = getattr(match, 'func', None) if match else None
        view_class = getattr(view_func, 'view_class', None)
        rule = None
        if view_class:
            model = getattr(view_class, 'model', None)
            if model:
                app_label = getattr(model._meta, 'app_label', None)
                model_name = getattr(model._meta, 'model_name', None)
                if app_label and model_name:
                    app_label = normalizar_app_label(app_label) 
                    if issubclass(view_class, CreateView):
                        acao = 'criar'
                    elif issubclass(view_class, UpdateView):
                        acao = 'editar'
                    elif issubclass(view_class, DeleteView):
                        acao = 'excluir'
                    elif issubclass(view_class, ListView):
                        acao = 'listar'
                    elif issubclass(view_class, DetailView):
                        acao = 'visualizar'
                    else:
                        acao = 'visualizar'
                    try:
                        self.logger.info(f"[perfil_mw] cbv view={view_class.__name__} app={app_label} model={model_name} acao={acao}")
                    except Exception:
                        pass
                    perfil = get_perfil_ativo(usuario)
                    try:
                        efet = sorted(list(acoes_permitidas(perfil, app_label, model_name)))
                        self.logger.info(f"[perfil_mw] efetivo app={app_label} model={model_name} acoes={efet}")
                    except Exception:
                        pass
                    permitido = tem_permissao(perfil, app_label, model_name, acao)
                    try:
                        self.logger.info(f"[perfil_mw] perfil={getattr(perfil,'perf_nome',None)} permitido={permitido}")
                    except Exception:
                        pass
                    if not permitido:
                        try:
                            messages.error(request, 'Acesso negado')
                        except Exception:
                            pass
                        return redirect('/web/home/')
                    return self.get_response(request)

        if request.path.startswith('/api/'):
            try:
                parts = request.path.strip('/').split('/')
                slug_part = parts[1] if len(parts) > 1 else None
                app_label = parts[2] if len(parts) > 2 else None
                model_token = parts[3] if len(parts) > 3 else None
                obj_id = parts[4] if len(parts) > 4 else None
                if app_label and model_token:
                    # Normaliza app_label imediatamente para garantir consistência
                    app_label = normalizar_app_label(app_label)
                    model_name = model_token.replace('-', '').replace('_', '')
                    method = request.method.upper()
                    if method == 'GET':
                        acao = 'visualizar' if obj_id else 'listar'
                    elif method == 'POST':
                        acao = 'criar'
                    elif method in ('PUT', 'PATCH'):
                        acao = 'editar'
                    elif method == 'DELETE':
                        acao = 'excluir'
                    else:
                        acao = 'visualizar'
                    try:
                        self.logger.info(f"[perfil_mw] api app={app_label} model={model_name} acao={acao} uid={getattr(usuario,'usua_codi',None)}")
                    except Exception:
                        pass
                    perfil = get_perfil_ativo(usuario)
                    try:
                        efet = sorted(list(acoes_permitidas(perfil, app_label, model_name)))
                        self.logger.info(f"[perfil_mw] efetivo app={app_label} model={model_name} acoes={efet}")
                    except Exception:
                        pass
                    permitido = tem_permissao(perfil, app_label, model_name, acao)
                    try:
                        self.logger.info(f"[perfil_mw] api perfil={getattr(perfil,'perf_nome',None)} permitido={permitido}")
                    except Exception:
                        pass
                    if not permitido:
                        return HttpResponseForbidden('Acesso negado')
            except Exception as e:
                try:
                    self.logger.warning(f"[perfil_mw] api_parse_error={e}")
                except Exception:
                    pass
        elif request.path.startswith('/web/'):
            try:
                parts = request.path.strip('/').split('/')
                # Formatos suportados:
                # /web/<slug>/<app>/(operacao|autocomplete|...)
                # /web/home/<slug>/<app>/(operacao|autocomplete|...)
                app_slug = None
                oper = ''
                if len(parts) >= 4 and parts[0] == 'web' and parts[1] == 'home':
                    app_slug = parts[3]
                    oper = parts[4] if len(parts) > 4 else ''
                elif len(parts) >= 3 and parts[0] == 'web':
                    app_slug = parts[2]
                    oper = parts[3] if len(parts) > 3 else ''
                if app_slug:
                    app_map = {
                        'contas-a-pagar': ('contas_a_pagar', 'titulospagar'),
                        'contas-a-receber': ('contas_a_receber', 'titulosreceber'),
                        'caixa-diario': ('CaixaDiario', 'caixageral'),
                        'dre': ('DRE', 'dre'),  # sem modelo direto; manter visualizar
                    }
                    app_label, default_model = app_map.get(app_slug, (None, None))
                    if app_label and default_model:
                        app_label = normalizar_app_label(app_label)
                        method = request.method.upper()
                        if oper.startswith('novo'):
                            acao = 'criar'
                        elif oper.startswith('editar'):
                            acao = 'editar'
                        elif oper.startswith('excluir'):
                            acao = 'excluir'
                        elif oper.startswith('autocomplete'):
                            acao = 'visualizar'
                        else:
                            acao = 'listar'
                        perfil = get_perfil_ativo(usuario)
                        try:
                            efet = sorted(list(acoes_permitidas(perfil, app_label, default_model)))
                            self.logger.info(f"[perfil_mw] efetivo app={app_label} model={default_model} acoes={efet}")
                        except Exception:
                            pass
                        permitido = tem_permissao(perfil, app_label, default_model, acao)
                        try:
                            self.logger.info(f"[perfil_mw] web app={app_label} model={default_model} acao={acao} permitido={permitido}")
                        except Exception:
                            pass
                        if not permitido:
                            try:
                                messages.error(request, 'Acesso negado')
                            except Exception:
                                pass
                            return redirect('/web/home/')
            except Exception as e:
                try:
                    self.logger.warning(f"[perfil_mw] web_parse_error={e}")
                except Exception:
                    pass

        # Fallback para rotas não baseadas em CBV com model definido
        if not match:
            return self.get_response(request)
        view_key = getattr(match, 'view_name', None) or getattr(match, 'url_name', None)
        rule = PERMISSION_MAP.get(view_key)
        try:
            self.logger.info(f"[perfil_mw] fallback view_key={view_key} rule={rule}")
        except Exception:
            pass

        if not rule:
            return self.get_response(request)

        ok = verificar_por_url(usuario, view_key) if usuario else True
        try:
            self.logger.info(f"[perfil_mw] verificar_por_url usuario={getattr(usuario,'usua_nome',None)} ok={ok}")
        except Exception:
            pass
        if not ok:
            try:
                messages.error(request, 'Acesso negado')
            except Exception:
                pass
            return redirect('/web/home/')

        return self.get_response(request)
