from rest_framework.exceptions import PermissionDenied
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps


# ============================
# SAFELIST PARA ROTAS PÚBLICAS
# ============================

PUBLIC_PATHS = {
    "/health",
    "/health/",
    "/api/health",
    "/api/health/",
}


def is_public_request(request):
    path = (request.path or "").rstrip("/")
    return path in PUBLIC_PATHS


# ============================
# LOADER DE MÓDULOS (BLINDADO)
# ============================

def get_modulos_usuario_db(request):
    try:
        # health-check não precisa ler licença, banco, JSON, nada
        if is_public_request(request):
            return ["__public__"]

        from core.utils import get_licenca_db_config
        from parametros_admin.models import PermissaoModulo

        banco = get_licenca_db_config(request)
        if not banco:
            return getattr(request, "modulos_disponiveis", [])

        def _to_int(v):
            try:
                return int(v)
            except Exception:
                return None

        # Resolve empresa/filial sem stepover esquisito
        empresa = (
            _to_int(request.headers.get("X-Empresa"))
            or _to_int(request.headers.get("Empresa_id"))
            or request.session.get("empresa_id")
            or _to_int(getattr(request.user, "usua_empr", None))
        )

        filial = (
            _to_int(request.headers.get("X-Filial"))
            or _to_int(request.headers.get("Filial_id"))
            or request.session.get("filial_id")
            or _to_int(getattr(request.user, "usua_fili", None))
        )

        # Se não existe empresa/filial → não trava, só retorna fallback
        if not empresa or not filial:
            return getattr(request, "modulos_disponiveis", [])

        permissoes = (
            PermissaoModulo.objects.using(banco)
            .filter(
                perm_empr=empresa,
                perm_fili=filial,
                perm_ativ=True,
                perm_modu__modu_ativ=True,
            )
            .select_related("perm_modu")
        )

        mod_db = [p.perm_modu.modu_nome for p in permissoes]

        mod_json = getattr(request, "modulos_disponiveis", [])

        # união rápida e direta
        return list({*mod_db, *mod_json})

    except Exception:
        return getattr(request, "modulos_disponiveis", [])


# ============================
# DECORATOR PARA MÉTODOS
# ============================

def modulo_necessario(nome_app):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(self, request, *args, **kwargs):
            if is_public_request(request):
                return view_func(self, request, *args, **kwargs)

            modulos = get_modulos_usuario_db(request)
            if nome_app not in modulos:
                raise PermissionDenied(f"Módulo '{nome_app}' não liberado.")
            return view_func(self, request, *args, **kwargs)
        return _wrapped
    return decorator


# ============================
# MIXIN PARA VIEWSET/VIEW
# ============================

class ModuloRequeridoMixin:
    modulo_requerido = None

    def dispatch(self, request, *args, **kwargs):
        # health-check nunca passa por checagem
        if is_public_request(request):
            return super().dispatch(request, *args, **kwargs)

        if self.modulo_requerido:
            modulos = get_modulos_usuario_db(request)
            if self.modulo_requerido not in modulos:
                # Se for WEB → redireciona
                if not request.path.startswith("/api"):
                    try:
                        messages.error(
                            request,
                            f"Módulo '{self.modulo_requerido}' não está liberado."
                        )
                    except Exception:
                        pass

                    slug = (
                        kwargs.get("slug")
                        or request.session.get("slug")
                    )

                    if slug:
                        return redirect(reverse("home_slug", kwargs={"slug": slug}))

                    return redirect(reverse("home"))

                # se for API → 403 limpo
                raise PermissionDenied(
                    f"Módulo '{self.modulo_requerido}' não está liberado."
                )

        return super().dispatch(request, *args, **kwargs)
