import time
import logging
from threading import local
from django.core.cache import cache
from django.conf import settings
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
            self._apply_empresa_filial(request, parts, pos_emp=3, pos_fil=4)

            return self._safe(request)

        # ---------------------------
        # 2. API: /api/<slug>/...
        # ---------------------------
        if not parts or parts[0] != "api":
            return self._safe(request)

        if len(parts) < 2:
            return self._bad("Slug ausente.")

        slug = parts[1]

        # slug null/undefined → tenta JWT
        if slug in ("null", "undefined"):
            slug = self._slug_from_jwt(request)

        lic = self._get_licenca(slug)
        if not lic:
            return self._bad(f"Licença {slug} inexistente.")

        request.slug = slug
        set_licenca_slug(slug)
        set_current_request(request)

        self._apply_empresa_filial_api(request)

        self._load_modulos(request)

        total = (time.time() - start) * 1000
        logger.debug("REQ OUT path=%s time=%.2fms", path, total)

        return self._safe(request)

    # ======================================================
    # Helpers
    # ======================================================

    def _apply_empresa_filial(self, request, parts, pos_emp, pos_fil):
        try:
            emp = int(parts[pos_emp]) if len(parts) > pos_emp else None
            fil = int(parts[pos_fil]) if len(parts) > pos_fil else None
        except Exception:
            return

        if emp and request.session.get("empresa_id") != emp:
            request.session["empresa_id"] = emp

        if fil and request.session.get("filial_id") != fil:
            request.session["filial_id"] = fil

        request.session.modified = True

    def _apply_empresa_filial_api(self, request):
        def _n(v):
            try:
                return int(v)
            except:
                return None

        h_emp = _n(request.headers.get("X-Empresa"))
        h_fil = _n(request.headers.get("X-Filial"))

        s_emp = request.session.get("empresa_id")
        s_fil = request.session.get("filial_id")

        emp = h_emp or s_emp or 1
        fil = h_fil or s_fil or 1

        change = False
        if h_emp is not None and h_emp != s_emp:
            request.session["empresa_id"] = h_emp
            change = True

        if h_fil is not None and h_fil != s_fil:
            request.session["filial_id"] = h_fil
            change = True

        if change:
            request.session.modified = True

        request.empresa = emp
        request.filial = fil

    def _load_modulos(self, request):
        slug = request.slug
        emp = request.empresa
        fil = request.filial

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

    def _slug_from_jwt(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        try:
            import jwt

            token = auth.split(" ")[1]
            dec = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return dec.get("lice_slug") or request.session.get("slug")
        except Exception as e:
            logger.error("Erro JWT: %s", e)
            return None

    def _get_licenca(self, slug):
        return next((x for x in get_licencas_map() if x["slug"] == slug), None)

    # ======================================================
    # Respostas seguras
    # ======================================================

    def _safe(self, request):
        try:
            return self.get_response(request)
        except RuntimeError as e:
            msg = str(e)
            if "session was deleted" in msg:
                from django.http import JsonResponse
                return JsonResponse(
                    {
                        "error": "Bad Request",
                        "code": "SESSION_INVALID",
                        "next": "/web/selecionar-empresa/",
                    },
                    status=401,
                )
            raise

    def _bad(self, msg):
        from django.http import JsonResponse

        logger.error("401 → %s", msg)
        return JsonResponse(
            {"error": msg, "code": "SESSION_INVALID", "next": "/web/selecionar-empresa/"},
            status=401,
        )
