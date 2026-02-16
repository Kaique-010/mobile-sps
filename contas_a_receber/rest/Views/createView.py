from rest_framework import status
from rest_framework.response import Response
from core.registry import get_licenca_db_config


def handle_create(viewset, request):
    banco = get_licenca_db_config(request)
    serializer = viewset.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    from ...services import criar_titulo_receber, gera_parcelas_a_receber
    empresa = (request.session.get('empresa_id')
           or request.headers.get('X-Empresa')
           or request.GET.get('titu_empr')
           or serializer.validated_data.get('titu_empr'))
    filial = (request.session.get('filial_id')
           or request.headers.get('X-Filial')
           or request.GET.get('titu_fili')
           or serializer.validated_data.get('titu_fili'))
    try:
        empresa = int(empresa) if empresa is not None else empresa
    except Exception:
        pass
    try:
        filial = int(filial) if filial is not None else filial
    except Exception:
        pass
    obj = criar_titulo_receber(banco=banco, dados=serializer.validated_data, empresa_id=empresa, filial_id= filial)
    gera_parcelas_a_receber(
        titulo=obj,
        banco=banco,
    )
    out = viewset.get_serializer(obj)
    return Response(out.data, status=status.HTTP_201_CREATED)
