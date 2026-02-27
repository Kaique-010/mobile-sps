from django.views.generic import ListView
from django.db.models import Q
from core.utils import get_licenca_db_config
from transportes.models import Veiculos

class VeiculosListView(ListView):
    model = Veiculos
    template_name = 'transportes/veiculos_lista.html'
    context_object_name = 'veiculos'
    paginate_by = 20

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get('empresa_id')
        qs = Veiculos.objects.using(banco).filter(veic_empr=empresa_id)
        
        # Filtro genérico (q)
        term = self.request.GET.get('q')
        if term:
            qs = qs.filter(
                Q(veic_plac__icontains=term) |
                Q(veic_frot__icontains=term) |
                Q(veic_sequ__icontains=term)
            )

        # Filtros específicos
        veic_tran = self.request.GET.get('veic_tran')
        if veic_tran:
            qs = qs.filter(veic_tran=veic_tran)

        veic_plac = self.request.GET.get('veic_plac')
        if veic_plac:
            qs = qs.filter(veic_plac__icontains=veic_plac)

        return qs.order_by('veic_tran', 'veic_sequ')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Veículos'
        # Contagem total para exibir no card (opcional, mas bom para UX)
        context['total_veiculos'] = self.get_queryset().count()
        return context
