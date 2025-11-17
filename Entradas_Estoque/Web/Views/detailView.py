from django.views.generic import DetailView
from ...models import EntradaEstoque
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
import logging
logger = logging.getLogger(__name__)



class EntradaDetailView(DetailView):
    model = EntradaEstoque
    template_name = 'Entradas/entrada_detalhe.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return EntradaEstoque.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        
        try:
            from Entidades.models import Entidades
            from Produtos.models import Produtos
            banco = get_licenca_db_config(self.request) or 'default'
            entrada = context.get('object')
            
            if entrada:
                entidade = Entidades.objects.using(banco).filter(
                    enti_clie=entrada.entr_enti
                ).values('enti_nome').first()
        except Exception as e:
                logger.error(f"Erro ao carregar entidade: {e}")
        return context
                                


