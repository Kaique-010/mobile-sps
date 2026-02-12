from .base import BaseListView
from Agricola.models import EventoAnimal, Animal
from core.utils import get_licenca_db_config

class EventoAnimalListView(BaseListView):
    model = EventoAnimal
    template_name = 'Agricola/evento_animal_list.html'
    context_object_name = 'eventos_animais'
    empresa_field = 'evnt_empr'
    filial_field = 'evnt_fili'
    order_by_field = '-evnt_data_even'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        
        if q:
            # Configurar DB para buscar animais
            db_name = get_licenca_db_config(self.request) or 'default'
            
            # Buscar IDs de animais que correspondem à pesquisa
            # Assumindo que evnt_anim guarda o ID do animal
            animais_ids = list(Animal.objects.using(db_name).filter(anim_ident__icontains=q).values_list('id', flat=True))
            animais_ids_str = [str(id) for id in animais_ids]
            
            from django.db.models import Q
            queryset = queryset.filter(
                Q(evnt_tipo_even__icontains=q) |
                Q(evnt_anim__in=animais_ids_str)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)        
        eventos = context.get('eventos_animais', [])
        
        # Obter IDs dos animais
        animais_ids = set()
        for evento in eventos:
            if evento.evnt_anim:
                try:
                    # Tenta converter para int pois o campo é CharField mas guarda ID
                    animais_ids.add(int(evento.evnt_anim))
                except (ValueError, TypeError):
                    pass
        
        if animais_ids:
            # Configurar DB
            db_name = get_licenca_db_config(self.request) or 'default'
            
            # Buscar animais
            animais = Animal.objects.using(db_name).filter(id__in=animais_ids)
            anim_map = {str(a.id): a for a in animais}
            
            # Anexar objeto animal ao evento
            for evento in eventos:
                # O campo evnt_anim original é o ID (str)
                animal_id = str(evento.evnt_anim)
                animal = anim_map.get(animal_id)
                
                if animal:
                    # Adiciona o campo display solicitado pelo usuário
                    animal.anim_ident_display = animal.anim_ident
                    # Substitui o ID pelo objeto Animal para o template acessar propriedades
                    evento.evnt_anim = animal
                else:
                    # Cria um objeto dummy ou dict para não quebrar o template
                    class AnimalDummy:
                        anim_ident = 'N/A'
                        anim_ident_display = 'N/A (Removido)'
                    evento.evnt_anim = AnimalDummy()
                
        return context

