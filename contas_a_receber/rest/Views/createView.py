from rest_framework import status
from rest_framework.response import Response
from core.registry import get_licenca_db_config


def handle_create(viewset, request):
    banco = get_licenca_db_config(request)
    serializer = viewset.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    from ...services import criar_titulo_receber
    emp = (request.session.get('empresa_id')
           or request.headers.get('X-Empresa')
           or request.GET.get('titu_empr')
           or serializer.validated_data.get('titu_empr'))
    fil = (request.session.get('filial_id')
           or request.headers.get('X-Filial')
           or request.GET.get('titu_fili')
           or serializer.validated_data.get('titu_fili'))
    try:
        emp = int(emp) if emp is not None else emp
    except Exception:
        pass
    try:
        fil = int(fil) if fil is not None else fil
    except Exception:
        pass
    obj = criar_titulo_receber(banco=banco, dados=serializer.validated_data, empresa_id=emp, filial_id=fil)
    out = viewset.get_serializer(obj)
    return Response(out.data, status=status.HTTP_201_CREATED)
