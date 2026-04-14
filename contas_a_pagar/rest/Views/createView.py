from rest_framework import status
from rest_framework.response import Response
from core.registry import get_licenca_db_config
from ...validators import validar_datas_titulo


def handle_create(viewset, request):
    banco = get_licenca_db_config(request)
    serializer = viewset.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    avisos = validar_datas_titulo(
        titu_emis=serializer.validated_data.get('titu_emis'),
        titu_venc=serializer.validated_data.get('titu_venc'),
    )

    from ...services import criar_titulo_pagar, gera_parcelas_a_pagar
    obj = criar_titulo_pagar(banco=banco, dados=serializer.validated_data)
    gera_parcelas_a_pagar(titulo=obj, banco=banco)
    out = viewset.get_serializer(obj)
    payload = dict(out.data)
    if avisos:
        payload['warnings'] = avisos
    return Response(payload, status=status.HTTP_201_CREATED)
