from django.views.generic import DetailView
from core.utils import get_licenca_db_config
from ...models import Orcamentos, ItensOrcamento

class OrcamentoPrintView(DetailView):
    model = Orcamentos
    template_name = 'Orcamentos/orcamento_impressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        return Orcamentos.objects.using(banco).filter(pedi_empr=empresa_id, pedi_fili=filial_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.object
        itens_qs = ItensOrcamento.objects.using(banco).filter(
            iped_empr=obj.pedi_empr, iped_fili=obj.pedi_fili, iped_pedi=str(obj.pedi_nume)
        ).order_by('iped_item')
        try:
            from Produtos.models import Produtos
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
        except Exception:
            context['itens_detalhados'] = [{'prod_codigo': i.iped_prod, 'prod_nome': i.iped_prod, 'has_foto': False,
                                             'iped_quan': i.iped_quan, 'iped_unit': i.iped_unit, 'iped_tota': i.iped_tota,
                                             'iped_item': getattr(i, 'iped_item', None)} for i in itens_qs]
        return context