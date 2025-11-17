from django.views.generic import DetailView
from core.utils import get_licenca_db_config
from ...models import Os

class OsDetailView(DetailView):
    model = Os
    template_name = 'Os/os_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Os.objects.using(banco).filter(
            os_empr=self.request.session.get('empresa_id', 1),
            os_fili=self.request.session.get('filial_id', 1),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            os = context.get('object')
            if os:
                cliente = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_clie
                ).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_resp
                ).values('enti_nome').first()
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else 'N/A'
                itens_qs = os.itens if hasattr(os, 'itens') else []
                try:
                    itens_qs = Produtos.objects.none()
                    from ..models import ItensOs
                    itens_qs = ItensOs.objects.using(banco).filter(
                        iped_empr=os.os_empr,
                        iped_fili=os.os_fili,
                        iped_os=str(os.os_nume)
                    ).order_by('peca_os')
                except Exception:
                    pass
                codigos = [i.peca_os for i in itens_qs]
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos)
                prod_map = {p.prod_codi: {'nome': p.prod_nome, 'has_foto': bool(p.prod_foto)} for p in produtos}
                itens_detalhados = []
                for i in itens_qs:
                    meta = prod_map.get(i.peca_os, {})
                    itens_detalhados.append({
                        'prod_codigo': i.peca_os,
                        'prod_nome': meta.get('nome') or i.peca_os,
                        'has_foto': bool(meta.get('has_foto')),
                        'peca_quan': i.peca_quan,
                        'peca_unit': i.peca_unit,
                        'peca_tota': i.peca_tota,
                        'peca_item': getattr(i, 'peca_item', None),
                    })
                context['itens_detalhados'] = itens_detalhados
        except Exception:
            context['cliente_nome'] = 'N/A'
            context['vendedor_nome'] = 'N/A'
        return context