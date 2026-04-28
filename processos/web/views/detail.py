# processos/web/views.py

from django.views.generic import  DetailView, View
from core.utils import get_licenca_db_config
from processos.models import Processo




class ProcessoDetailView(DetailView):
    model = Processo
    template_name = "processos/processo_detail.html"
    context_object_name = "processo"
    def __init__(self, *args, **kwargs):
        self.banco = get_licenca_db_config(self.request) or 'default'
        self.empresa_id = self.request.session.get('empresa_id', 1)
        self.filial_id = self.request.session.get('filial_id', 1)
        super().__init__(*args, **kwargs)
    
    def get_queryset(self):
        return Processo.objects.using(self.banco).filter(
            proc_empr=self["proc_empr__exact"],
            proc_fili=self["filial__exact"],
        ).select_related("proc_tipo").prefetch_related("respostas")


