from django.http import JsonResponse
from django.views import View

from core.utils import get_licenca_db_config
from O_S.services.rentabilidade import RentabilidadeOsService

class OsRentabilidadeView(View):
    def get(self, request, *args, **kwargs):
        slug = kwargs.get("slug")
        os_id = kwargs.get("pk")
        banco = get_licenca_db_config(slug)

        if not banco:
            return JsonResponse({"erro": "Banco de dados não encontrado para a licença informada."}, status=400)

        empresa_id = request.session.get("empresa_id")
        filial_id = request.session.get("filial_id")

        if not empresa_id or not filial_id:
            return JsonResponse({"erro": "Empresa ou filial não definida na sessão."}, status=400)

        data = RentabilidadeOsService.calcular_os(
            banco=banco,
            os_id=os_id,
            empresa=empresa_id,
            filial=filial_id,
        )

        if not data:
            return JsonResponse({"erro": "Não foi possível calcular a rentabilidade da OS."}, status=400)

        return JsonResponse(data, status=200)
