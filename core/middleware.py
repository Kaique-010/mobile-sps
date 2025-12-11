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

        logger.debug(
            "REQ IN   path=%s method=%s cookies=%s session_keys=%s",
            request.path, request.method,
            request.META.get('HTTP_COOKIE'),
            list(request.session.keys())[:20],
        )

        # -----------------------------------------------------------
        # 1. IGNORAR ROTAS QUE NÃO USAM LICENÇA
        # -----------------------------------------------------------
        ignored = [
            '/api/warm-cache/', '/api/licencas/mapa/',
            '/api/selecionar-empresa/', '/api/entidades-login/',
            '/web/', '/admin/', '/static/', '/media/', '/ws/',
            '/api/schema/', '/api/swagger', '/api/schemas/',
        ]
        for prefix in ignored:
            if request.path.startswith(prefix):
                logger.debug("IGNORED path=%s", request.path)
                return self._safe_response(request)

        # -----------------------------------------------------------
        # 2. TRATAMENTO WEB / SLUG / EMPRESA / FILIAL
        # -----------------------------------------------------------
        parts = request.path.strip("/").split("/")

        if len(parts) >= 2 and parts[0] == "web" and parts[1] == "home":
            logger.debug("WEB FLOW parts=%s", parts)

            # Tela de seleção de empresa NÃO deve carregar licenças
            if len(parts) >= 3 and parts[2] == "selecionar-empresa":
                logger.debug("Tela de seleção detectada, passando direto")
                return self._safe_response(request)

            slug = parts[2] if len(parts) >= 3 else None

            if slug:
                logger.debug("WEB SLUG=%s", slug)
            else:
                logger.warning("WEB sem slug, tentando recuperar do session.docu")
                return self._safe_response(request)

            lic = next((l for l in get_licencas_map() if l["slug"] == slug), None)
            if not lic:
                logger.error("Slug inexistente WEB slug=%s", slug)
                from django.http import HttpResponseNotFound
                return HttpResponseNotFound("Licença não encontrada.")

            set_licenca_slug(slug)
            request.slug = slug
            set_current_request(request)

            # Empresa/filial no path
            if len(parts) >= 5:
                try:
                    emp = int(parts[3])
                    fil = int(parts[4])

                    logger.info("WEB emp=%s fil=%s", emp, fil)

                    if request.session.get("empresa_id") != emp:
                        request.session["empresa_id"] = emp
                        request.session.modified = True

                    if request.session.get("filial_id") != fil:
                        request.session["filial_id"] = fil
                        request.session.modified = True

                except Exception as e:
                    logger.error("Falha ao aplicar empresa/filial WEB: %s", e)

            return self._safe_response(request)

        # -----------------------------------------------------------
        # 3. API — SLUG DEVE EXISTIR EM /api/<slug>/...
        # -----------------------------------------------------------
        if not parts or parts[0] != "api":
            return self._safe_response(request)

        if len(parts) < 2:
            logger.error("API sem slug no path=%s", request.path)
            return self._bad_request("API malformatada. Faltando slug.")

        slug = parts[1]
        logger.debug("API SLUG=%s", slug)

        # Slug null/undefined → extrai do JWT
        if slug in ["null", "undefined"]:
            logger.warning("Slug null/undefined, tentando JWT")
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                return self._bad_request("Token ausente ao tentar recuperar slug.")

            try:
                import jwt
                token = auth.split(" ")[1]
                dec = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                slug = dec.get("lice_slug") or request.session.get("slug")
                logger.info("Slug recuperado via JWT: slug=%s", slug)
            except Exception as e:
                return self._bad_request(f"Erro JWT: {e}")

        lic = next((l for l in get_licencas_map() if l["slug"] == slug), None)
        if not lic:
            return self._bad_request(f"Licença slug {slug} não encontrada.")

        set_licenca_slug(slug)
        request.slug = slug
        set_current_request(request)

        # -----------------------------------------------------------
        # 4. EMPRESA/FILIAL — cabeçalho > sessão
        # -----------------------------------------------------------
        def _num(v): 
            try: return int(v)
            except: return None

        h_emp = _num(request.headers.get("X-Empresa"))
        h_fil = _num(request.headers.get("X-Filial"))

        s_emp = request.session.get("empresa_id")
        s_fil = request.session.get("filial_id")

        empresa = h_emp or s_emp or 1
        filial = h_fil or s_fil or 1

        logger.debug("Empresa/Filial — header=(%s,%s) session=(%s,%s) final=(%s,%s)",
                    h_emp, h_fil, s_emp, s_fil, empresa, filial)
        try:
            logger.debug("[TRACE][MW] slug=%s empresa=%s filial=%s path=%s", slug, empresa, filial, request.path)
        except Exception:
            pass

        if h_emp is not None and s_emp != h_emp:
            request.session["empresa_id"] = h_emp
            request.session.modified = True

        if h_fil is not None and s_fil != h_fil:
            request.session["filial_id"] = h_fil
            request.session.modified = True

        # -----------------------------------------------------------
        # 5. CACHE DE MÓDULOS
        # -----------------------------------------------------------
        key = f"mod_{slug}_{empresa}_{filial}"
        mods = cache.get(key)

        if mods:
            logger.debug("CACHE HIT key=%s count=%s", key, len(mods))
        else:
            logger.debug("CACHE MISS key=%s → consultando banco", key)
            try:
                from parametros_admin.models import PermissaoModulo
                banco = get_licenca_db_config(request)

                if banco:
                    qs = PermissaoModulo.objects.using(banco).filter(
                        perm_empr=empresa,
                        perm_fili=filial,
                        perm_ativ=True,
                        perm_modu__modu_ativ=True,
                    ).select_related("perm_modu")

                    mods = [x.perm_modu.modu_nome for x in qs]
                    cache.set(key, mods, 1800)

                else:
                    mods = []

            except Exception as e:
                logger.error("Erro ao consultar módulos: %s", e)
                mods = []

        set_modulos_disponiveis(mods)
        request.modulos_disponiveis = mods
        total = (time.time() - start) * 1000
        logger.debug("REQ OUT path=%s time=%.2fms", request.path, total)

        return self._safe_response(request)

    def _safe_response(self, request):
        try:
            return self.get_response(request)
        except RuntimeError as e:
            msg = str(e)
            try:
                accept = request.META.get("HTTP_ACCEPT", "")
            except Exception:
                accept = ""
            try:
                path = request.path or ""
            except Exception:
                path = ""
            if "session was deleted" in msg or "session was deleted before the request completed" in msg:
                if path.startswith("/api/") or "application/json" in accept:
                    from django.http import JsonResponse
                    return JsonResponse({
                        "error": "Bad Request",
                        "code": "SESSION_INVALID",
                        "next": "/web/selecionar-empresa/"
                    }, status=401)
                try:
                    from django.shortcuts import redirect
                    return redirect("web_login")
                except Exception:
                    from django.http import HttpResponseRedirect
                    return HttpResponseRedirect("/web/login/")
            raise

    def _bad_request(self, msg):
        from django.http import JsonResponse
        logger.error("401 ERROR → %s", msg)
        next_url = "/web/selecionar-empresa/"
        return JsonResponse({"error": msg, "code": "SESSION_INVALID", "next": next_url}, status=401)
