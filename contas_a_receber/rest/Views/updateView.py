from rest_framework.response import Response
from core.registry import get_licenca_db_config


def handle_update(viewset, request, *, partial=False):
    banco = get_licenca_db_config(request)
    instance = viewset.get_object()
    serializer = viewset.get_serializer(instance, data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    from ...services import atualizar_titulo_receber
    obj = atualizar_titulo_receber(instance, banco=banco, dados=serializer.validated_data)
    out = viewset.get_serializer(obj)
    return Response(out.data)