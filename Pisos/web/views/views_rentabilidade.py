
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from core.utils import get_db_from_slug
from Pisos.services.rentabilidade_service import RentabilidadeService


@login_required
@require_GET
def rentabilidade_documento(request, slug, tipo, numero):
    try:
        banco = get_db_from_slug(slug)

        resultado = RentabilidadeService.calcular_documento(
            tipo=tipo,
            numero=numero,
            banco=banco,
        )

        # Converte Decimal para string sem perder precisão.
        def converter(valor):
            if hasattr(valor, "as_tuple"):
                return str(valor)
            raise TypeError(
                f"Tipo não serializável: {type(valor).__name__}"
            )

        return JsonResponse(
            resultado,
            json_dumps_params={"default": converter},
        )

    except ValueError as exc:
        return JsonResponse({"erro": str(exc)}, status=400)

    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Erro ao calcular rentabilidade."
        )
        return JsonResponse(
            {"erro": "Não foi possível calcular a rentabilidade."},
            status=500,
        )
