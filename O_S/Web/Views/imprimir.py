from django.views.generic import DetailView
from core.utils import get_licenca_db_config
from ...models import Os

class OsPrintView(DetailView):
    model = Os
    template_name = 'Os/os_impressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Os.objects.using(banco).filter(
            os_empr=self.request.session.get('empresa_id', 1),
            os_fili=self.request.session.get('filial_id', 1),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')
        try:
            from Entidades.models import Entidades
            banco = get_licenca_db_config(self.request) or 'default'
            os = context.get('object')
            if os:
                cliente = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_forn
                ).values('enti_nome').first()
                vendedor = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_vend
                ).values('enti_nome').first()
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['vendedor_nome'] = vendedor.get('enti_nome') if vendedor else 'N/A'
                context['itens_detalhados'] = []
        except Exception:
            context['cliente_nome'] = 'N/A'
            context['vendedor_nome'] = 'N/A'
        return context