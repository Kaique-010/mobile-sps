from cgitb import reset
from django.views.generic import DetailView
from core.utils import get_licenca_db_config
from ...models import Osexterna

class OsPrintView(DetailView):
    model = Osexterna
    template_name = 'Osexterna/oseximpressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return Osexterna.objects.using(banco).filter(
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
                resposnsavel = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_vend
                ).values('enti_nome').first()
                context['cliente_nome'] = cliente.get('enti_nome') if cliente else 'N/A'
                context['resposnsavel_nome'] = resposnsavel.get('enti_nome') if resposnsavel else 'N/A'
                context['itens_detalhados'] = []
        except Exception:
            context['cliente_nome'] = 'N/A'
            context['resposnsavel_nome'] = 'N/A'
        return context