from .base import BaseListView
from Agricola.models import AplicacaoInsumos, ProdutoAgro, Talhao
from core.utils import get_licenca_db_config

class AplicacaoInsumosListView(BaseListView):
    model = AplicacaoInsumos
    template_name = 'Agricola/aplicacao_insumos_list.html'
    context_object_name = 'aplicacoes_insumos'
    empresa_field = 'apli_empr'
    filial_field = 'apli_fili'
    order_by_field = '-apli_data'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aplicacoes = context.get('aplicacoes_insumos', [])
        
        # Coletar IDs para busca em lote
        prod_ids = set()
        talh_ids = set()
        
        for app in aplicacoes:
            if app.apli_prod:
                prod_ids.add(app.apli_prod)
            if app.apli_talh:
                talh_ids.add(app.apli_talh)
        
        # Determinar banco de dados
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        # Buscar objetos relacionados
        produtos = {}
        if prod_ids:
            produtos = {str(p.pk): p for p in ProdutoAgro.objects.using(db_name).filter(pk__in=prod_ids)}
            
        talhoes = {}
        if talh_ids:
            talhoes = {str(t.pk): t for t in Talhao.objects.using(db_name).filter(pk__in=talh_ids)}
            
        # Anexar objetos às instâncias de aplicação
        for app in aplicacoes:
            app.produto_obj = produtos.get(str(app.apli_prod))
            app.talhao_obj = talhoes.get(str(app.apli_talh))
            
        return context

    