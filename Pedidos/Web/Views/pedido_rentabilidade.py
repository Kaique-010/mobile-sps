from django.http import JsonResponse
from django.views import View
from core.utils import get_licenca_db_config
from Pedidos.services.rentabilidade import RentabilidadeService
from ...models import PedidoVenda

class PedidoRentabilidadeView(View):
    def get(self, request, slug=None, pk=None, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id") or request.headers.get("X-Empresa") or request.GET.get("empresa")
        filial = request.session.get("filial_id") or request.headers.get("X-Filial") or request.GET.get("filial")
        produto = request.GET.get("produto") or ""

        try:
            pedido = (
                PedidoVenda.objects.using(banco)
                .filter(pedi_empr=int(empresa), pedi_fili=int(filial), pedi_nume=int(pk))
                .first()
            )
        except Exception:
            pedido = None

        if not pedido:
            return JsonResponse({"erro": "Pedido não encontrado."}, status=404)

        data = RentabilidadeService.calcular_pedido(
            banco=banco,
            pedido_id=pedido.pedi_nume,
            empresa=pedido.pedi_empr,
            filial=pedido.pedi_fili,
            produto=produto,
        )
        if not data:
            return JsonResponse({"erro": "Não foi possível calcular a rentabilidade."}, status=400)

        return JsonResponse(data, status=200)
