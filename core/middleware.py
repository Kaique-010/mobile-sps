import time
import logging
from threading import local
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from core.licenca_context import set_current_request, get_licencas_map
from core.utils import get_licenca_db_config

logger = logging.getLogger("licenca.middleware")

_local = local()

def set_licenca_slug(slug):
    _local.licenca_slug = slug

def get_licenca_slug():
    return getattr(_local, 'licenca_slug', None)

def set_modulos_disponiveis(modulos):
    _local.modulos_disponiveis = modulos

def get_modulos_disponiveis():
    return getattr(_local, 'modulos_disponiveis', [])


class LicencaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()

        path = request.path or ""
        parts = path.strip("/").split("/")

        logger.debug("REQ path=%s method=%s", path, request.method)

        # ---------------------------
        # 0. Rotas ignoradas
        # ---------------------------
        ignored = (
            "/api/warm-cache/",
            "/api/licencas/mapa/",
            "/api/selecionar-empresa/",
            "/api/entidades-login/",
            "/web/",
            "/admin/",
            "/static/",
            "/media/",
            "/ws/",
            "/api/schema/",
            "/api/swagger",
            "/api/schemas/",
        )

        for prefix in ignored:
            if path.startswith(prefix):
                return self._safe(request)
        
        # Ignorar rota específica de login de entidades com slug
        # /api/<slug>/entidades/login/
        if len(parts) >= 4 and parts[2] == "entidades" and parts[3] == "login":
             return self._safe(request)

        # ---------------------------
        # 1. WEB: /web/home/<slug>/...
        # ---------------------------
        if len(parts) >= 2 and parts[0] == "web" and parts[1] == "home":

            # Exceção: tela de seleção
            if len(parts) >= 3 and parts[2] == "selecionar-empresa":
                return self._safe(request)

            slug = parts[2] if len(parts) >= 3 else None
            if not slug:
                logger.warning("WEB sem slug")
                return self._safe(request)

            lic = self._get_licenca(slug)
            if not lic:
                return self._not_found("Licença não encontrada.")

            request.slug = slug
            set_licenca_slug(slug)
            set_current_request(request)

            # Empresa e filial: /web/home/<slug>/<emp>/<fil>/
            self._apply_empresa_filial_safe(request, parts, pos_emp=3, pos_fil=4)

            return self._safe(request)

        # ---------------------------
        # 2. API: /api/<slug>/...
        # ---------------------------
        if not parts or parts[0] != "api":
            return self._safe(request)

        if len(parts) < 2:
            return self._bad("Slug ausente.")

        slug = parts[1]

        # Rotas especiais de API que recebem o slug depois da ação,
        # por exemplo: /api/emitir/<slug>/<id>/ ou /api/imprimir/<slug>/<id>/
        if slug in ("emitir", "imprimir") and len(parts) >= 3:
            slug = parts[2]

        if slug in ("null", "undefined"):
            slug = self._slug_from_jwt(request)

        lic = self._get_licenca(slug)

        if not lic:
            sessao_slug = None
            try:
                if hasattr(request, "session") and request.session is not None:
                    sessao_slug = request.session.get("slug")
            except Exception:
                sessao_slug = None

            if not sessao_slug:
                try:
                    sessao_slug = get_licenca_slug()
                except Exception:
                    sessao_slug = None

            if (getattr(request, "user", None) and getattr(request.user, "is_authenticated", False)) and sessao_slug:
                alt = self._get_licenca(sessao_slug)
                if alt:
                    logger.warning(
                        "Slug %s não encontrado no mapa de licenças, reaproveitando slug de contexto %s para usuário autenticado %s",
                        slug,
                        sessao_slug,
                        getattr(request.user, "username", None),
                    )
                    slug = sessao_slug
                    lic = alt

        if not lic:
            return self._bad(f"Licença {slug} inexistente.")

        request.slug = slug
        set_licenca_slug(slug)
        set_current_request(request)

        self._apply_empresa_filial_api_safe(request)

        self._load_modulos(request)

        total = (time.time() - start) * 1000
        logger.debug("REQ OUT path=%s time=%.2fms", path, total)

        return self._safe(request)

    # ======================================================
    # Helpers - COM PROTEÇÃO CONTRA SESSÃO DELETADA
    # ======================================================

    def _session_get(self, request, key, default=None):
        """Acessa sessão com proteção contra sessão deletada."""
        try:
            if not hasattr(request, 'session') or request.session is None:
                return default
            return request.session.get(key, default)
        except (AttributeError, RuntimeError) as e:
            logger.warning("Erro ao acessar sessão: %s", e)
            return default

    def _session_set(self, request, key, value):
        """Modifica sessão com proteção contra sessão deletada."""
        try:
            if not hasattr(request, 'session') or request.session is None:
                return False
            
            # Só modifica se o valor realmente mudou
            current = request.session.get(key)
            if current != value:
                request.session[key] = value
                request.session.modified = True
            return True
        except (AttributeError, RuntimeError) as e:
            logger.warning("Erro ao modificar sessão: %s", e)
            return False

    def _apply_empresa_filial_safe(self, request, parts, pos_emp, pos_fil):
        """Aplica empresa/filial com proteção contra sessão deletada."""
        try:
            emp = int(parts[pos_emp]) if len(parts) > pos_emp else None
            fil = int(parts[pos_fil]) if len(parts) > pos_fil else None
        except (ValueError, IndexError):
            return

        if emp:
            self._session_set(request, "empresa_id", emp)

        if fil:
            self._session_set(request, "filial_id", fil)

    def _apply_empresa_filial_api_safe(self, request):
        """Aplica empresa/filial da API com proteção contra sessão deletada."""
        def _n(v):
            try:
                return int(v)
            except:
                return None

        h_emp = _n(request.headers.get("X-Empresa"))
        h_fil = _n(request.headers.get("X-Filial"))

        s_emp = self._session_get(request, "empresa_id")
        s_fil = self._session_get(request, "filial_id")

        # Headers têm prioridade, depois sessão, depois default
        emp = h_emp if h_emp is not None else (s_emp or 1)
        fil = h_fil if h_fil is not None else (s_fil or 1)

        # Só atualiza sessão se veio nos headers E é diferente
        if h_emp is not None and h_emp != s_emp:
            self._session_set(request, "empresa_id", h_emp)

        if h_fil is not None and h_fil != s_fil:
            self._session_set(request, "filial_id", h_fil)

        # Sempre define no request (independente da sessão)
        request.empresa = emp
        request.filial = fil

    def _load_modulos(self, request):
        """Carrega módulos com tratamento de erro."""
        slug = getattr(request, 'slug', None)
        emp = getattr(request, 'empresa', 1)
        fil = getattr(request, 'filial', 1)

        if not slug:
            request.modulos_disponiveis = []
            return

        key = f"mod_{slug}_{emp}_{fil}"
        mods = cache.get(key)

        if mods is None:
            try:
                from parametros_admin.models import PermissaoModulo
                banco = get_licenca_db_config(request)

                if banco:
                    qs = (
                        PermissaoModulo.objects.using(banco)
                        .filter(
                            perm_empr=emp,
                            perm_fili=fil,
                            perm_ativ=True,
                            perm_modu__modu_ativ=True,
                        )
                        .select_related("perm_modu")
                    )
                    mods = [x.perm_modu.modu_nome for x in qs]
                else:
                    mods = []

                cache.set(key, mods, 1800)
            except Exception as e:
                logger.error("Erro ao carregar módulos: %s", e)
                mods = []

        request.modulos_disponiveis = mods
        set_modulos_disponiveis(mods)

    def _slug_from_jwt(self, request):
        """Extrai slug do JWT com fallback para sessão."""
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return self._session_get(request, "slug")
        
        try:
            import jwt

            token = auth.split(" ")[1]
            dec = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            slug = dec.get("lice_slug")
            
            if slug:
                return slug
            
            # Fallback para sessão
            return self._session_get(request, "slug")
        except Exception as e:
            logger.error("Erro JWT: %s", e)
            return self._session_get(request, "slug")

    def _get_licenca(self, slug):
        """Busca licença no mapa."""
        if not slug:
            return None
        return next((x for x in get_licencas_map() if x["slug"] == slug), None)

    # ======================================================
    # Respostas seguras
    # ======================================================

    def _safe(self, request):
        """Executa response com tratamento de sessão deletada."""
        try:
            return self.get_response(request)
        except (RuntimeError, SuspiciousOperation) as e:
            msg = str(e)
            if "session was deleted" in msg or "session" in msg.lower():
                logger.warning("Sessão deletada durante requisição: %s", msg)
                return JsonResponse(
                    {
                        "error": "Session expired",
                        "code": "SESSION_INVALID",
                        "next": "/web/selecionar-empresa/",
                    },
                    status=401,
                )
            raise

    def _bad(self, msg):
        """Resposta de erro de autenticação."""
        logger.error("401 → %s", msg)
        return JsonResponse(
            {
                "error": msg,
                "code": "SESSION_INVALID",
                "next": "/web/selecionar-empresa/",
            },
            status=401,
        )

    def _not_found(self, msg):
        """Resposta de recurso não encontrado."""
        logger.error("404 → %s", msg)
        return JsonResponse(
            {
                "error": msg,
                "code": "NOT_FOUND",
            },
            status=404,
        )
