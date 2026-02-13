from .base import BaseListView
from Agricola.models import MovimentacaoEstoque, Fazenda, ProdutoAgro
from core.utils import get_licenca_db_config

class MovimentacaoEstoqueListView(BaseListView):
    model = MovimentacaoEstoque
    template_name = 'Agricola/movimentacao_estoque_list.html'
    context_object_name = 'movimentacoes_estoque'
    empresa_field = 'movi_estq_empr'
    filial_field = 'movi_estq_fili'
    order_by_field = '-movi_estq_data'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Determine database to use
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')

        # Get list of unique Fazenda IDs and Produto IDs from the queryset
        # Note: We use self.object_list which is already filtered by base view
        movimentacoes = context['movimentacoes_estoque']
        
        faze_ids = set(m.movi_estq_faze for m in movimentacoes if m.movi_estq_faze)
        prod_ids = set(m.movi_estq_prod for m in movimentacoes if m.movi_estq_prod)

        # Fetch names manually
        fazendas = {
            str(f.id): f.faze_nome 
            for f in Fazenda.objects.using(db_name).filter(id__in=faze_ids)
        }
        
        produtos = {
            str(p.id): p.prod_nome_agro 
            for p in ProdutoAgro.objects.using(db_name).filter(id__in=prod_ids)
        }

        # Attach names to each object for the template
        for mov in movimentacoes:
            faze_id = str(mov.movi_estq_faze)
            prod_id = str(mov.movi_estq_prod)
            
            mov.faze_nome_display = fazendas.get(faze_id, f"Fazenda {faze_id}")
            mov.prod_nome_display = produtos.get(prod_id, f"Produto {prod_id}")

        return context
