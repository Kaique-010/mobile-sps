from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction
from datetime import date
from core.utils import get_licenca_db_config
from ...models import Orcamentos, ItensOrcamento
from Pedidos.models import PedidoVenda, Itenspedidovenda

@require_http_methods(["POST"])
def transformar_em_pedido_web(request, pk, slug=None):
    banco = get_licenca_db_config(request)
    if not banco:
        messages.error(request, 'Banco de dados não encontrado')
        return redirect('OrcamentosWeb:orcamentos_listar', slug=slug)
    try:
        orcamento = Orcamentos.objects.using(banco).filter(pk=pk).first()
        if not orcamento:
            messages.error(request, 'Orçamento não encontrado')
            return redirect('OrcamentosWeb:orcamentos_listar', slug=slug)
        with transaction.atomic(using=banco):
            ultimo = PedidoVenda.objects.using(banco).filter(
                pedi_empr=orcamento.pedi_empr,
                pedi_fili=orcamento.pedi_fili
            ).order_by('-pedi_nume').first()
            proximo = (ultimo.pedi_nume + 1) if ultimo else 1
            while PedidoVenda.objects.using(banco).filter(pedi_nume=proximo).exists():
                proximo += 1
            pedido = PedidoVenda.objects.using(banco).create(
                pedi_empr=orcamento.pedi_empr,
                pedi_fili=orcamento.pedi_fili,
                pedi_nume=proximo,
                pedi_forn=orcamento.pedi_forn,
                pedi_data=date.today(),
                pedi_tota=orcamento.pedi_tota,
                pedi_desc=orcamento.pedi_desc,
                pedi_topr=orcamento.pedi_topr,
                pedi_canc=False,
                pedi_fina='0',
                pedi_vend=orcamento.pedi_vend or '0',
                pedi_stat='0',
                pedi_obse=orcamento.pedi_obse or ''
            )
            itens = ItensOrcamento.objects.using(banco).filter(
                iped_empr=orcamento.pedi_empr,
                iped_fili=orcamento.pedi_fili,
                iped_pedi=str(orcamento.pedi_nume)
            )
            for it in itens:
                Itenspedidovenda.objects.using(banco).create(
                    iped_empr=it.iped_empr,
                    iped_fili=it.iped_fili,
                    iped_pedi=str(pedido.pedi_nume),
                    iped_item=it.iped_item,
                    iped_prod=it.iped_prod,
                    iped_quan=it.iped_quan,
                    iped_unit=it.iped_unit,
                    iped_suto=it.iped_unit,
                    iped_tota=it.iped_tota,
                    iped_fret=0,
                    iped_desc=it.iped_desc,
                    iped_unli=it.iped_unli,
                    iped_forn=it.iped_forn,
                    iped_vend=None,
                    iped_cust=0,
                    iped_tipo=None,
                    iped_desc_item=False,
                    iped_perc_desc=it.iped_pdes_item,
                    iped_unme=None,
                )
            orcamento.pedi_nume_pedi = pedido.pedi_nume
            orcamento.pedi_stat = '2'
            orcamento.save(using=banco)
        messages.success(request, f'Orçamento {orcamento.pedi_nume} transformado em pedido {pedido.pedi_nume}.')
    except Exception as e:
        messages.error(request, f'Erro ao transformar orçamento: {e}')
    return redirect('OrcamentosWeb:orcamentos_listar', slug=slug)