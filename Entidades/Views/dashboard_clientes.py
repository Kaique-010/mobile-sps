from rest_framework import viewsets
from rest_framework.permissions import BasePermission
from .base_cliente import IsCliente
from Pedidos.models import PedidoVenda, Itenspedidovenda
from Orcamentos.models import Orcamentos, ItensOrcamento
from O_S.models import OrdemServicoGeral, Os
from OrdemdeServico.models import Ordemservico
from django.db.models import Sum, Q
from rest_framework.permissions import IsAuthenticated



class ClienteDashboardViewSet(viewsets.ViewSet): 
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        cliente_id = request.cliente_id
        banco = request.banco
        
        
        total_pedidos = PedidoVenda.objects.using(banco).filter(pedi_forn=cliente_id).count()
        total_orcamentos = Orcamentos.objects.using(banco).filter(pedi_forn=cliente_id).count()
        total_ordens_servico = Ordemservico.objects.using(banco).filter(orde_enti=cliente_id).count()
        total_os = Os.objects.using(banco).filter(os_clie=cliente_id).count()
        total_itens_pedidos = Itenspedidovenda.objects.using(banco).filter(iped_forn=cliente_id).count()
        total_itens_orcamentos = ItensOrcamento.objects.using(banco).filter(iped_forn=cliente_id).count()
        total_valor_pedidos = Itenspedidovenda.objects.using(banco).filter(iped_forn=cliente_id).aggregate(Sum('iped_valor'))['iped_valor__sum'] or 0
        total_valor_orcamentos = ItensOrcamento.objects.using(banco).filter(iped_forn=cliente_id).aggregate(Sum('iped_valor'))['iped_valor__sum'] or 0
        total_valor_ordens_servico = Ordemservico.objects.using(banco).filter(orde_enti=cliente_id).aggregate(Sum('orde_valor'))['orde_valor__sum'] or 0
        total_valor_os = Os.objects.using(banco).filter(os_clie=cliente_id).aggregate(Sum('os_valor'))['os_valor__sum'] or 0
        total_valor_total = total_valor_pedidos + total_valor_orcamentos + total_valor_ordens_servico + total_valor_os
        total_valor_total = round(total_valor_total, 2)

        dashboard_data = {
            'total_pedidos': total_pedidos,
            'total_orcamentos': total_orcamentos, 
            'total_ordens_servico': total_ordens_servico,
            'total_os': total_os,
            'total_itens_pedidos': total_itens_pedidos,
            'total_itens_orcamentos': total_itens_orcamentos,
            'total_valor_pedidos': total_valor_pedidos,
            'total_valor_orcamentos': total_valor_orcamentos,
            'total_valor_ordens_servico': total_valor_ordens_servico,
            'total_valor_os': total_valor_os,
            'total_valor_total': total_valor_total, 
        }
        
        return Response(dashboard_data)










