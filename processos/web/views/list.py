from django.views.generic import ListView
from core.utils import get_licenca_db_config
from processos.models import Processo
from processos.services.processo_service import ProcessoService

class ProcessoListView(ListView):
    model = Processo
    template_name = "processos/processo_list.html"
    context_object_name = "processos"
    def __init__(self, *args, **kwargs):
        self.banco = get_licenca_db_config(self.request) or 'default'
        self.empresa_id = self.request.session.get('empresa_id', 1)
        self.filial_id = self.request.session.get('filial_id', 1)
        super().__init__(*args, **kwargs)
    
    def get_queryset(self):
        ctx = self.get_context_base()
        ctx["db_alias"] = self.banco
        ctx["empresa_id"] = self.empresa_id
        ctx["filial_id"] = self.filial_id
        return ProcessoService.listar(
            db_alias=ctx["db_alias"],
            empresa_id=ctx["empresa_id"],
            filial_id=ctx["filial_id"], 
        )
