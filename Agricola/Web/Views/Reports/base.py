from django.views.generic import TemplateView
from core.utils import get_licenca_db_config

class BaseReportView(TemplateView):
    template_name = None
    title = ""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        
        # Configurações de DB e Empresa/Filial
        self.db_name = get_licenca_db_config(self.request) or 'default'
        self.empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
        self.filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
        
        return context
