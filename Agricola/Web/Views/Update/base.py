from django.views.generic.edit import UpdateView
from core.utils import get_licenca_db_config
from django.shortcuts import redirect
import logging

logger = logging.getLogger(__name__)

class BaseUpdateView(UpdateView):
    model = None
    form_class = None
    template_name = None
    success_url = None
    empresa_field = None
    filial_field = None
    usuario_field = None
    # Flag to control if user filtering should be applied in get_queryset
    filter_by_user = False 

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        # print(f"BaseUpdateView.get_queryset: using db={db_name}, model={self.model.__name__}")
        
        queryset = self.model.objects.using(db_name)
        
        if self.empresa_field and self.filial_field:
            empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
            filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
            
            # print(f"BaseUpdateView.get_queryset: filtering by empresa={empresa}, filial={filial}, usuario={usuario}")
            
            filters = {
                self.empresa_field: empresa,
                self.filial_field: filial
            }
            
            # Only filter by user if explicitly enabled
            if self.usuario_field and self.filter_by_user:
                usuario = getattr(self.request.user, 'id', None) or self.request.session.get('usuario_id', 1)
                # print(f"BaseUpdateView.get_queryset: filtering by usuario={usuario}")
                filters[self.usuario_field] = usuario
                
            queryset = queryset.filter(**filters)
            # print(f"BaseUpdateView.get_queryset result count: {queryset.count()}")
            # print(f"BaseUpdateView.get_queryset SQL: {queryset.query}")
            
        return queryset

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        self.object = form.save(commit=False)
        
        # If usuario_field is defined, update it to the current user
        if self.usuario_field:
            usuario = getattr(self.request.user, 'id', None) or self.request.session.get('usuario_id', 1)
            setattr(self.object, self.usuario_field, usuario)
            
        self.object.save(using=db_name)
        form.save_m2m()
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'update'
        return context
