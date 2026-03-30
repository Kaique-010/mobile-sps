from django.db import transaction
from django.db.models import Sum
from GestaoObras.models import Obra, ObraLancamentoFinanceiro


class CapexService:
    @staticmethod
    def saldo_planejado(banco: str, obra: Obra):
        return obra.obra_orca

    @staticmethod
    def saldo_realizado(banco: str, obra: Obra):
        qs = ObraLancamentoFinanceiro.objects.using(banco).filter(lfin_obra=obra, lfin_tipo="DE")
        total = qs.aggregate(total=Sum("lfin_valo")).get("total") or 0
        return total

    @staticmethod
    def registrar_baixa(banco: str, obra: Obra, valor, categoria: str, descricao: str, data):
        dados = {
            "lfin_empr": obra.obra_empr,
            "lfin_fili": obra.obra_fili,
            "lfin_obra": obra,
            "lfin_tipo": "DE",
            "lfin_cate": categoria,
            "lfin_desc": descricao,
            "lfin_valo": valor,
            "lfin_dcom": data,
        }
        with transaction.atomic(using=banco):
            return ObraLancamentoFinanceiro.objects.using(banco).create(**dados)
