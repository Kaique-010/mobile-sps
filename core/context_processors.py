from typing import Dict, Any

from django.http import HttpRequest

try:
    from Licencas.models import Empresas, Filiais
except Exception:
    Empresas = None
    Filiais = None

try:
    from Licencas.permissions import usuario_privilegiado
except Exception:
    usuario_privilegiado = None

try:
    from core.utils import get_licenca_db_config
except Exception:
    get_licenca_db_config = None

def empresa_filial_names(request: HttpRequest) -> Dict[str, Any]:
    """
    Adiciona ao contexto os nomes de Empresa e Filial, quando disponíveis.
    Utiliza o banco da licença identificado pelo middleware.

    Contexto retornado:
      - empresa_id: código da empresa (da sessão)
      - filial_id: código da filial (da sessão)
      - empresa_nome: nome da empresa (do banco da licença)
      - filial_nome: nome da filial (do banco da licença)
    """
    contexto = {
        "empresa_id": None,
        "filial_id": None,
        "empresa_nome": None,
        "filial_nome": None,
    }

    try:
        empresa_id = request.session.get("empresa_id")
        filial_id = request.session.get("filial_id")
        contexto["empresa_id"] = empresa_id
        contexto["filial_id"] = filial_id

        if not (Empresas and Filiais and get_licenca_db_config):
            # Caso as importações falhem em algum contexto, retornamos apenas os IDs
            return contexto

        banco = get_licenca_db_config(request)

        # Nome da empresa pelo código (empr_codi)
        if banco and empresa_id is not None:
            empresa = (
                Empresas.objects.using(banco)
                .filter(empr_codi=empresa_id)
                .only("empr_nome")
                .first()
            )
            if empresa:
                contexto["empresa_nome"] = getattr(empresa, "empr_nome", None)

        # Nome da filial pelo código da filial (empr_empr)
        if banco and filial_id is not None:
            filial = (
                Filiais.objects.using(banco)
                .filter(empr_empr=filial_id)
                .only("empr_nome")
                .first()
            )
            if filial:
                contexto["filial_nome"] = getattr(filial, "empr_nome", None)

    except Exception:
        # Em caso de qualquer erro de lookup, mantemos fallback para IDs
        pass

    return contexto


def auth_menu_flags(request: HttpRequest) -> Dict[str, Any]:
    can_view_admin_menus = False
    try:
        user = getattr(request, "user", None)
        is_auth = user is not None and getattr(user, "is_authenticated", False)

        # Sem autenticação, nem tenta — evita False negativo por sessão vazia
        if not is_auth:
            return {"can_view_admin_menus": False}

        if usuario_privilegiado:
            can_view_admin_menus = usuario_privilegiado(request)
    except Exception:
        can_view_admin_menus = False
    return {"can_view_admin_menus": can_view_admin_menus}