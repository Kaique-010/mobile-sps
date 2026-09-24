
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.utils.text import slugify

from core.utils import get_db_from_slug


@dataclass(frozen=True)
class ContextoConciliacao:
    slug: str
    db_alias: str
    empresa: int
    filial: int


def obter_contexto(request, slug, acao="view"):
    if acao not in ("view", "add"):
        raise PermissionDenied("Ação não permitida.")

    db_alias = get_db_from_slug(slug)

    empresa = (
        request.session.get("empresa_id")
        or request.session.get("empresa")
    )
    filial = (
        request.session.get("filial_id")
        or request.session.get("filial")
    )

    if not empresa or not filial:
        raise PermissionDenied(
            "Sessão inválida: empresa/filial não informadas."
        )

    try:
        empresa = int(empresa)
        filial = int(filial)
    except (TypeError, ValueError):
        raise PermissionDenied(
            "Empresa ou filial inválida."
        )

    return ContextoConciliacao(
        slug=slug,
        db_alias=db_alias,
        empresa=empresa,
        filial=filial,
    )