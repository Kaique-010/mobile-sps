from .base import BaseListView
from Agricola.models import EstoqueFazenda, Fazenda, ProdutoAgro
from Agricola.service.parametros import ParametroAgricolaService
from core.utils import get_licenca_db_config

class EstoqueFazendaListView(BaseListView):
    model = EstoqueFazenda
    template_name = 'Agricola/estoque_fazenda_list.html'
    context_object_name = 'estoques_fazenda'
    empresa_field = 'estq_empr'
    filial_field = 'estq_fili'
    order_by_field = 'id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Determine database to use
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')

        # Get list of unique Fazenda IDs and Produto IDs from the queryset
        estoques = context['estoques_fazenda']
        
        faze_ids = set(e.estq_faze for e in estoques if e.estq_faze)
        prod_ids = set(e.estq_prod for e in estoques if e.estq_prod)

        # Fetch objects manually
        fazendas = {
            str(f.id): f 
            for f in Fazenda.objects.using(db_name).filter(id__in=faze_ids)
        }
        
        produtos = {
            str(p.id): p 
            for p in ProdutoAgro.objects.using(db_name).filter(id__in=prod_ids)
        }

        # Attach objects to each item for the template
        for estoque in estoques:
            faze_id = str(estoque.estq_faze)
            prod_id = str(estoque.estq_prod)
            
            estoque.faze_obj = fazendas.get(faze_id)
            estoque.prod_obj = produtos.get(prod_id)
            
        return context
