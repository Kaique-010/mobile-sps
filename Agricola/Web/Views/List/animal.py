from .base import BaseListView
from Agricola.models import Animal, Fazenda
from core.utils import get_licenca_db_config

class AnimalListView(BaseListView):
    model = Animal
    template_name = 'Agricola/animal_list.html'
    context_object_name = 'animais'
    empresa_field = 'anim_empr'
    filial_field = 'anim_fili'
    order_by_field = 'anim_ident'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animais = context.get('animais', [])
        
        # Obter IDs das fazendas
        fazenda_ids = set(t.anim_faze for t in animais if t.anim_faze)
        
        if fazenda_ids:
            # Configurar DB
            banco = get_licenca_db_config(self.request) or 'default'
            db_name = banco['db_name'] if isinstance(banco, dict) else 'default'
            
            # Buscar fazendas
            fazendas = Fazenda.objects.using(db_name).filter(id__in=fazenda_ids)
            faze_map = {f.id: f.faze_nome for f in fazendas}
            
            # Anexar nome da fazenda aos objetos de animal
            for animal in animais:
                animal.faze_nome_display = faze_map.get(animal.anim_faze, 'N/A')
                
        return context
