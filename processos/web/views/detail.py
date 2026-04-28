# processos/web/views.py

from django.views.generic import  DetailView, View
from core.utils import get_licenca_db_config
from processos.models import Processo




class ProcessoDetailView(DetailView):
    model = Processo
    template_name = "processos/processo_detail.html"
    context_object_name = "processo"
    banco = get_licenca_db_config(self.request) or 'default'
    empresa_id = self.request.session.get('empresa_id', 1)
    filial_id = self.request.session.get('filial_id', 1)
    
    def get_queryset(self):
        return Processo.objects.using(self.banco).filter(
            proc_empr=self.empresa_id,
            proc_fili=self.filial_id,   
        ).select_related("proc_tipo").prefetch_related("respostas")


