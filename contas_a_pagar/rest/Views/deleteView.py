from rest_framework import status
from rest_framework.response import Response
from core.registry import get_licenca_db_config


def handle_delete(viewset, request):
    banco = get_licenca_db_config(request)
    instance = viewset.get_titulo_for_historico()
    from ...services import excluir_titulo_pagar
    excluir_titulo_pagar(instance, banco=banco)
    return Response(status=status.HTTP_204_NO_CONTENT)