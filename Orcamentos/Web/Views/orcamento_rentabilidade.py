from django.http import JsonResponse
from django.views import View

from core.utils import get_licenca_db_config
from Orcamentos.services.rentabilidade import RentabilidadeOrcamentoService
from ...models import Orcamentos


class OrcamentoRentabilidadeView(View):
    def get(self, request, slug=None, pk=None, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id") or request.headers.get("X-Empresa") or request.GET.get("empresa")
        filial = request.session.get("filial_id") or request.headers.get("X-Filial") or request.GET.get("filial")
        produto = request.GET.get("produto") or ""

        try:
            orcamento = (
                Orcamentos.objects.using(banco)
                .filter(pedi_empr=int(empresa), pedi_fili=int(filial), pedi_nume=int(pk))
                .first()
            )
        except Exception:
            orcamento = None

        if not orcamento:
            return JsonResponse({"erro": "Orçamento não encontrado."}, status=404)

        data = RentabilidadeOrcamentoService.calcular_orcamento(
            banco=banco,
            orcamento_id=orcamento.pedi_nume,
            empresa=orcamento.pedi_empr,
            filial=orcamento.pedi_fili,
            produto=produto,
        )
        if not data:
            return JsonResponse({"erro": "Não foi possível calcular a rentabilidade."}, status=400)

        return JsonResponse(data, status=200)

