from django.views.generic.edit import CreateView
from django.shortcuts import redirect
from django.contrib import messages

from core.utils import get_licenca_db_config
from processos.models import Processo



    

class ProcessoCreateView(CreateView):
    model = Processo
    template_name = "processos/processo_create.html"
    context_object_name = "processo"
    banco = get_licenca_db_config(self.request) or 'default'
    empresa_id = self.request.session.get('empresa_id', 1)
    filial_id = self.request.session.get('filial_id', 1)
    
    def form_valid(self, form):
        form.instance.empresa_id = self.empresa_id
        form.instance.filial_id = self.filial_id    
        form.save(using=self.banco)
        messages.success(self.request, "Processo criado com sucesso.")
        return redirect("processos:detalhe", pk=form.instance.pk)
    
    
    def get_context_base(self):
        ctx = super().get_context_base()
        ctx["db_alias"] = self.banco
        ctx["empresa_id"] = self.empresa_id
        ctx["filial_id"] = self.filial_id
        ctx["proc_empr__exact"] = self.empresa_id
        ctx["filial__exact"] = self.filial_id
        return ctx



