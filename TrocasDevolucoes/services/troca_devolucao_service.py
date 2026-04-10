from decimal import Decimal
from django.db import transaction
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
        with transaction.atomic(using=banco):
            tot_devo = Decimal('0.00')
            tot_repo = Decimal('0.00')
            for it in itens or []:
                tot_devo += Decimal(str(it.get('itdv_vlor') or 0))
                tot_repo += Decimal(str(it.get('itdv_vlre') or 0))
            dados.setdefault('tdvl_tode', tot_devo)
            dados.setdefault('tdvl_tore', tot_repo)
            dados.setdefault('tdvl_safi', (dados.get('tdvl_tode') or Decimal('0.00')) - (dados.get('tdvl_tore') or Decimal('0.00')))

            troca = TrocaDevolucao.objects.using(banco).create(tdvl_nume=numero, **dados)

            for idx, item in enumerate(itens or [], start=1):
                ItensTrocaDevolucao.objects.using(banco).create(
                    itdv_empr=dados['tdvl_empr'],
                    itdv_fili=dados['tdvl_fili'],
                    itdv_tdvl=numero,
                    itdv_item=idx,
                    **item,
                )

            if str(dados.get('tdvl_stat')) == '2':
                TrocaDevolucaoService._processar_movimentacoes(banco, troca)

            return troca

    @staticmethod
    def atualizar(banco, instance, dados):
        status_anterior = str(getattr(instance, 'tdvl_stat', '0') or '0')
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        instance.save(using=banco)
        if str(getattr(instance, 'tdvl_stat', '0')) == '2' and status_anterior != '2':
            TrocaDevolucaoService._processar_movimentacoes(banco, instance)
        return instance

    @staticmethod
    def atualizar_itens(banco, instance, itens):
        with transaction.atomic(using=banco):
            ItensTrocaDevolucao.objects.using(banco).filter(
                itdv_empr=instance.tdvl_empr,
                itdv_fili=instance.tdvl_fili,
                itdv_tdvl=instance.tdvl_nume,
            ).delete()
            for idx, item in enumerate(itens or [], start=1):
                ItensTrocaDevolucao.objects.using(banco).create(
                    itdv_empr=instance.tdvl_empr,
                    itdv_fili=instance.tdvl_fili,
                    itdv_tdvl=instance.tdvl_nume,
                    itdv_item=idx,
                    **item,
                )

    @staticmethod
    def _proximo_sequencial(using, model, field_name):
        ultimo = model.objects.using(using).aggregate(mx=Max(field_name)).get('mx') or 0
        try:
            return int(ultimo) + 1
        except Exception:
            return 1

    @staticmethod
    def _processar_movimentacoes(banco, instance):
        from Saidas_Estoque.models import SaidasEstoque
        from Entradas_Estoque.models import EntradaEstoque
        from adiantamentos.services import AdiantamentosService

        itens = ItensTrocaDevolucao.objects.using(banco).filter(
            itdv_empr=instance.tdvl_empr,
            itdv_fili=instance.tdvl_fili,
            itdv_tdvl=instance.tdvl_nume,
        )

        with transaction.atomic(using=banco):
            proximo_saida = TrocaDevolucaoService._proximo_sequencial(banco, SaidasEstoque, 'said_sequ')
            proximo_entrada = TrocaDevolucaoService._proximo_sequencial(banco, EntradaEstoque, 'entr_sequ')
            obs_base = f"{'Troca' if str(instance.tdvl_tipo) == 'TROC' else 'Devolução'} {instance.tdvl_nume} - Pedido {instance.tdvl_pdor}"

            for it in itens:
                qtd_origem = Decimal(str(getattr(it, 'itdv_qtor', 0) or 0))
                val_origem = Decimal(str(getattr(it, 'itdv_vlor', 0) or 0))
                prod_origem = str(getattr(it, 'itdv_pror', '') or '')
                if qtd_origem and prod_origem:
                    EntradaEstoque.objects.using(banco).create(
                        entr_empr=instance.tdvl_empr,
                        entr_fili=instance.tdvl_fili,
                        entr_sequ=proximo_entrada,
                        entr_data=instance.tdvl_data,
                        entr_prod=prod_origem,
                        entr_quan=qtd_origem,
                        entr_tota=val_origem,
                        entr_obse=obs_base,
                        entr_usua=1,
                        entr_enti=str(instance.tdvl_clie or '')[:10] or None,
                    )
                    proximo_entrada += 1

                if str(instance.tdvl_tipo) == 'TROC':
                    prod_repo = str(getattr(it, 'itdv_prre', '') or '')
                    qtd_repo = Decimal(str(getattr(it, 'itdv_qtre', 0) or 0))
                    val_repo = Decimal(str(getattr(it, 'itdv_vlre', 0) or 0))
                    if prod_repo and qtd_repo:
                        SaidasEstoque.objects.using(banco).create(
                            said_empr=instance.tdvl_empr,
                            said_fili=instance.tdvl_fili,
                            said_sequ=proximo_saida,
                            said_data=instance.tdvl_data,
                            said_prod=prod_repo,
                            said_quan=qtd_repo,
                            said_tota=val_repo,
                            said_obse=obs_base,
                            said_usua=1,
                            said_enti=str(instance.tdvl_clie or '')[:10] or None,
                        )
                        proximo_saida += 1
            try:
                valor_saldo = Decimal(str(getattr(instance, 'tdvl_safi', 0) or 0))
                if valor_saldo > 0:
                    dados = {
                        'adia_empr': instance.tdvl_empr,
                        'adia_fili': instance.tdvl_fili,
                        'adia_enti': instance.tdvl_clie,
                        'adia_docu': str(instance.tdvl_nume),
                        'adia_seri': 'TDVL',
                        'adia_tipo': 'CRED_TROCA',
                        'adia_valo': valor_saldo,
                        'adia_sald': valor_saldo,
                    }
                    AdiantamentosService.criar_adiantamento(dados=dados, using=banco)
            except Exception:
                pass
