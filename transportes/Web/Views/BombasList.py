from django.views.generic import ListView
from django.db.models import Q
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Bombas

class BombasListView(ListView):
    model = Bombas
    template_name = 'transportes/bombas_lista.html'
    context_object_name = 'bombas'
    paginate_by = 20

    def _get_banco(self):
        slug = self.kwargs.get('slug')
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_queryset(self):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id') 
        qs = Bombas.objects.using(banco).filter(bomb_empr=empresa_id)
        
        # Filtro genérico (q)
        term = self.request.GET.get('q')
        if term:
            qs = qs.filter(
                Q(bomb_codi__icontains=term) | 
                Q(bomb_desc__icontains=term)
                
            )



        bomb_desc = self.request.GET.get('bomb_desc')
        if bomb_desc:
            qs = qs.filter(bomb_desc__icontains=bomb_desc)
        
        return qs.order_by('bomb_desc', 'bomb_codi')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)        
        context['titulo'] = 'Bombas'
        # Contagem total para exibir no card
        context['total_bombas'] = self.get_queryset().count()   


        return context
