from django.db.models import Max

from TrocasDevolucoes.models import TrocaDevolucao, ItensTrocaDevolucao


class TrocaDevolucaoService:
    @staticmethod
    def listar(banco, filtros=None):
        filtros = filtros or {}
        qs = TrocaDevolucao.objects.using(banco).all().order_by('-tdvl_nume')
        if filtros.get('tdvl_empr'):
            qs = qs.filter(tdvl_empr=filtros['tdvl_empr'])
        if filtros.get('tdvl_fili'):
            qs = qs.filter(tdvl_fili=filtros['tdvl_fili'])
        if filtros.get('tdvl_pdor'):
            qs = qs.filter(tdvl_pdor=filtros['tdvl_pdor'])
        if filtros.get('tdvl_stat'):
            qs = qs.filter(tdvl_stat=filtros['tdvl_stat'])
        return qs

    @staticmethod
    def _proximo_numero(banco, empresa, filial):
        ultimo = (
            TrocaDevolucao.objects.using(banco)
            .filter(tdvl_empr=empresa, tdvl_fili=filial)
            .aggregate(Max('tdvl_nume'))
            .get('tdvl_nume__max')
            or 0
        )
        return int(ultimo) + 1

    @staticmethod
    def criar_com_itens(banco, dados, itens):
        numero = TrocaDevolucaoService._proximo_numero(banco, dados['tdvl_empr'], dados['tdvl_fili'])
        troca = TrocaDevolucao.objects.using(banco).create(tdvl_nume=numero, **dados)

        for idx, item in enumerate(itens or [], start=1):
            ItensTrocaDevolucao.objects.using(banco).create(
                itdv_empr=dados['tdvl_empr'],
                itdv_fili=dados['tdvl_fili'],
                itdv_tdvl=numero,
                itdv_item=idx,
                **item,
            )
        return troca

    @staticmethod
    def atualizar(banco, instance, dados):
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        instance.save(using=banco)
        return instance
