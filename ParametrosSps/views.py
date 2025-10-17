# Create your views here.
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Parametros
from .serializers import ParametrosPedidosSerializer
from core.utils import get_licenca_db_config

class ParametrosViewSet(viewsets.ViewSet):
    """
    Exposição de parâmetros de configuração da empresa.
    """

    @action(detail=False, methods=['get'])
    def configuracoes(self, request, slug=None):
        """
        Retorna os parâmetros globais necessários pro front.
        Exemplo: cancelamento de pedidos, limites, flags etc.
        """
        banco = get_licenca_db_config(request)
        empresa = getattr(request.user, "empresa_id", 1)

        try:
            parametro = Parametros.objects.using(banco).get(empresa_id=empresa)
            data = {
                "pedido_cancelamento_habilitado": bool(
                    parametro.pedido_cancelamento_habilitado
                ),
            }
            return Response(data)
        except Parametros.DoesNotExist:
            return Response(
                {"pedido_cancelamento_habilitado": False}, status=200
            )
