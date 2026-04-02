from .base import BaseListView
from django.db.models import Q
from Agricola.models import Animal, Fazenda
from core.utils import get_licenca_db_config

class AnimalListView(BaseListView):
    model = Animal
    template_name = 'Agricola/animal_list.html'
    context_object_name = 'animais'
    empresa_field = 'anim_empr'
    filial_field = 'anim_fili'
    order_by_field = 'anim_ident'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco['db_name'] if isinstance(banco, dict) else 'default'
        qs = Animal.objects.using(db_name).all()
        empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
        filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
        qs = qs.filter(anim_empr=empresa, anim_fili=filial)

        q = (self.request.GET.get('q') or '').strip()
        raca = (self.request.GET.get('raca') or '').strip()
        if q:
            qs = qs.filter(Q(anim_ident__icontains=q) | Q(anim_raca__icontains=q))
        if raca:
            qs = qs.filter(anim_raca__iexact=raca)

        return qs.order_by(self.order_by_field)[:100]

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
        
        # Lista de raças disponíveis para o filtro
        try:
            banco = get_licenca_db_config(self.request) or 'default'
            db_name = banco['db_name'] if isinstance(banco, dict) else 'default'
            racas = (Animal.objects.using(db_name)
                     .exclude(anim_raca__isnull=True)
                     .exclude(anim_raca='')
                     .values_list('anim_raca', flat=True)
                     .distinct()
                     .order_by('anim_raca'))
            context['racas'] = racas
        except Exception:
            context['racas'] = []

        return context
