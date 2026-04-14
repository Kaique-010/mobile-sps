from rest_framework.response import Response
from core.registry import get_licenca_db_config
from ...validators import validar_datas_titulo


def handle_update(viewset, request, *, partial=False):
    banco = get_licenca_db_config(request)
    instance = viewset.get_object()
    serializer = viewset.get_serializer(instance, data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    avisos = validar_datas_titulo(
        titu_emis=serializer.validated_data.get('titu_emis', instance.titu_emis),
        titu_venc=serializer.validated_data.get('titu_venc', instance.titu_venc),
    )

    from ...services import atualizar_titulo_pagar
    obj = atualizar_titulo_pagar(instance, banco=banco, dados=serializer.validated_data)
    out = viewset.get_serializer(obj)
    payload = dict(out.data)
    if avisos:
        payload['warnings'] = avisos
    return Response(payload)
