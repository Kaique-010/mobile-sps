from django.db.models import F, Sum

from GestaoObras.models import Obra, ObraLancamentoFinanceiro, ObraMaterialMovimento


class ObrasService:
    @staticmethod
    def consolidar_custo_obra(obra: Obra) -> Obra:
        total_materiais = (
            ObraMaterialMovimento.objects.filter(movm_obra=obra, movm_tipo="SA")
            .annotate(valor_total=F("movm_quan") * F("movm_cuni"))
            .aggregate(total=Sum("valor_total"))
            .get("total")
            or 0
        )
        total_despesas = (
            ObraLancamentoFinanceiro.objects.filter(lfin_obra=obra, lfin_tipo="DE")
            .aggregate(total=Sum("lfin_valo"))
            .get("total")
            or 0
        )
        obra.obra_cust = total_materiais + total_despesas
        obra.save(update_fields=["obra_cust", "obra_alte"])
        return obra
