from django.views.generic import TemplateView
import logging
from django.db.models import Sum, Count
from core.utils import get_licenca_db_config
from ...models import PedidosGeral

logger = logging.getLogger(__name__)


class PedidosDashboardView(TemplateView):
    template_name = 'Pedidos/pedidos_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        qs = PedidosGeral.objects.using(banco).all()
        empresa = self.request.session.get('empresa_id') or self.request.headers.get('X-Empresa') or self.request.GET.get('empresa')
        filial = self.request.session.get('filial_id') or self.request.headers.get('X-Filial') or self.request.GET.get('filial')
        data_inicial = self.request.GET.get('data_inicial')
        data_final = self.request.GET.get('data_final')
        vendedor = (self.request.GET.get('vendedor') or self.request.GET.get('nome_vendedor') or '').strip()
        cliente = (self.request.GET.get('cliente') or self.request.GET.get('nome_cliente') or '').strip()

        if empresa:
            qs = qs.filter(empresa=empresa)
        if filial:
            qs = qs.filter(filial=filial)
        if data_inicial:
            qs = qs.filter(data_pedido__gte=data_inicial)
        if data_final:
            qs = qs.filter(data_pedido__lte=data_final)
        if vendedor:
            qs = qs.filter(nome_vendedor__icontains=vendedor)
        if cliente:
            qs = qs.filter(nome_cliente__icontains=cliente)

        total_pedidos = qs.count()
        total_valor = qs.aggregate(Sum('valor_total')).get('valor_total__sum') or 0
        print(f"total_valor: {total_valor}")
        total_quantidade = qs.aggregate(Sum('quantidade_total')).get('quantidade_total__sum') or 0
        print(f"total_quantidade: {total_quantidade}")
        ticket_medio = float(total_valor) / float(total_pedidos) if total_pedidos else 0
        print(f"ticket_medio: {ticket_medio}")

        top_vendedores = list(
            qs.values('nome_vendedor').annotate(qtd=Count('numero_pedido'), valor=Sum('valor_total')).order_by('-valor')[:5]
        )
        series_diaria = list(
            qs.values('data_pedido').annotate(qtd=Count('numero_pedido'), valor=Sum('valor_total')).order_by('data_pedido')[:30]
        )

        try:
            from core.middleware import get_licenca_slug
            slug_val = self.kwargs.get('slug') or get_licenca_slug()
        except Exception:
            slug_val = self.kwargs.get('slug')

        ctx.update({
            'slug': slug_val,
            'filtros': {
                'empresa': empresa,
                'filial': filial,
                'data_inicial': data_inicial,
                'data_final': data_final,
                'vendedor': vendedor,
                'cliente': cliente,
            },
            'kpis': {
                'total_pedidos': total_pedidos,
                'total_valor': total_valor,
                'total_quantidade': total_quantidade,
                'ticket_medio': ticket_medio,
            },
            'top_vendedores': top_vendedores,
            'series_diaria': series_diaria,
        })
        return ctx