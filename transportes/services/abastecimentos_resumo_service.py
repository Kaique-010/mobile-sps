from django.core.exceptions import FieldError

from transportes.models import Abastecusto


class AbastecimentosResumoService:
    @staticmethod
    def listar_ultimos(
        *,
        banco: str,
        empresa_id: int,
        filial_id: int | None,
        frota_id: str | None,
        veiculo_sequ: int | None,
        limit: int = 10,
    ):
        qs = Abastecusto.objects.using(banco).filter(abas_empr=empresa_id)
        if filial_id:
            qs = qs.filter(abas_fili=filial_id)

        if frota_id not in (None, ""):
            qs = qs.filter(abas_frot=str(frota_id))

        if veiculo_sequ not in (None, ""):
            try:
                qs = qs.filter(abas_veic_sequ=int(veiculo_sequ))
            except FieldError:
                pass

        rows = list(
            qs.order_by("-abas_data", "-abas_ctrl")
            .values(
                "abas_ctrl",
                "abas_data",
                "abas_frot",
                "abas_bomb",
                "abas_comb",
                "abas_quan",
                "abas_unit",
                "abas_tota",
                "abas_hokm",
                "abas_hokm_ante",
                "abas_obse",
            )[: int(limit)]
        )

        out = []
        for r in rows:
            out.append(
                {
                    "controle": r.get("abas_ctrl"),
                    "data": r.get("abas_data"),
                    "frota_id": r.get("abas_frot"),
                    "bomba_codigo": r.get("abas_bomb"),
                    "combustivel_codigo": r.get("abas_comb"),
                    "quantidade": r.get("abas_quan"),
                    "valor_unitario": r.get("abas_unit"),
                    "total": r.get("abas_tota"),
                    "horimetro": r.get("abas_hokm"),
                    "horimetro_anterior": r.get("abas_hokm_ante"),
                    "observacoes": r.get("abas_obse"),
                }
            )
        return out

