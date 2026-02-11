from .base import BaseListView
from Agricola.models import Talhao, Fazenda
from core.utils import get_licenca_db_config

class TalhaoListView(BaseListView):
    model = Talhao
    template_name = 'Agricola/talhao_list.html'
    context_object_name = 'talhoes'
    empresa_field = 'talh_empr'
    filial_field = 'talh_fili'
    order_by_field = 'talh_nome'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        talhoes = context.get('talhoes', [])
        
        # Obter IDs das fazendas
        faze_ids = set(t.talh_faze for t in talhoes if t.talh_faze)
        
        if faze_ids:
            # Configurar DB
            banco = get_licenca_db_config(self.request) or 'default'
            db_name = banco['db_name'] if isinstance(banco, dict) else 'default'
            
            # Buscar fazendas
            fazendas = Fazenda.objects.using(db_name).filter(id__in=faze_ids)
            faze_map = {f.id: f.faze_nome for f in fazendas}
            
            # Anexar nome da fazenda aos objetos de talhão
            for talhao in talhoes:
                talhao.faze_nome_display = faze_map.get(talhao.talh_faze, 'N/A')
                
        return context
