from django.views.generic import DetailView
from django.http import Http404
import logging
from core.utils import get_licenca_db_config
from ...models import PedidoVenda

logger = logging.getLogger(__name__)


class PedidoDetailView(DetailView):
    model = PedidoVenda
    template_name = 'Pedidos/pedido_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        return PedidoVenda.objects.using(banco).filter(
            pedi_empr=int(empresa_id),
            pedi_fili=int(filial_id)
        )

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        try:
            pk = int(self.kwargs.get(self.pk_url_kwarg))
        except Exception:
            raise Http404("Pedido inválido")
        obj = queryset.filter(pedi_nume=pk).first()
        if not obj:
            raise Http404("Pedido não encontrado")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')

        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            pedido = context.get('object')

            if pedido:
                cliente = Entidades.objects.using(banco).filter(
                    enti_clie=pedido.pedi_forn
                ).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(
                    enti_clie=pedido.pedi_vend
                ).values('enti_nome').first()

                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else 'N/A'

                itens_qs = (
                    pedido.itens if hasattr(pedido, 'itens') else []
                )
                try:
                    itens_qs = Produtos.objects.none()
                    from ...models import Itenspedidovenda
                    itens_qs = Itenspedidovenda.objects.using(banco).filter(
                        iped_empr=pedido.pedi_empr,
                        iped_fili=pedido.pedi_fili,
                        iped_pedi=str(pedido.pedi_nume)
                    ).order_by('iped_item')
                except Exception:
                    pass

                codigos = [i.iped_prod for i in itens_qs]
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: {'nome': p.prod_nome, 'has_foto': bool(p.prod_foto)} for p in produtos}

                itens_detalhados = []
                for i in itens_qs:
                    meta = prod_map.get(i.iped_prod, {})
                    itens_detalhados.append({
                        'prod_codigo': i.iped_prod,
                        'prod_nome': meta.get('nome') or i.iped_prod,
                        'has_foto': bool(meta.get('has_foto')),
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                        'iped_tota': i.iped_tota,
                        'iped_item': getattr(i, 'iped_item', None),
                    })
                context['itens_detalhados'] = itens_detalhados
        except Exception as e:
            print(f"Erro ao carregar nomes: {e}")
            context['cliente_nome'] = 'N/A'
            context['vendedor_nome'] = 'N/A'

        return context
