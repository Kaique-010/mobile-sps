from django.views.generic.edit import UpdateView
from core.utils import get_licenca_db_config
from django.shortcuts import redirect

class BaseUpdateView(UpdateView):
    model = None
    form_class = None
    template_name = None
    success_url = None
    empresa_field = None
    filial_field = None

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco['db_name'] if isinstance(banco, dict) else 'default'
        
        queryset = self.model.objects.using(db_name)
        
        if self.empresa_field and self.filial_field:
            empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
            filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
            
            filters = {
                self.empresa_field: empresa,
                self.filial_field: filial
            }
            queryset = queryset.filter(**filters)
            
        return queryset

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco['db_name'] if isinstance(banco, dict) else 'default'
        
        self.object = form.save(commit=False)
        self.object.save(using=db_name)
        form.save_m2m()
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'update'
        return context
