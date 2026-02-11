from django.views.generic.edit import CreateView
from core.utils import get_licenca_db_config
from django.shortcuts import redirect

class BaseCreateView(CreateView):
    model = None
    form_class = None
    template_name = None
    success_url = None
    empresa_field = None
    filial_field = None

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        self.object = form.save(commit=False)
        
        # Atribui empresa e filial se os campos estiverem definidos
        if self.empresa_field and self.filial_field:
            empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
            filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
            
            # Precisamos atribuir a instância do objeto (Foreign Key) se o campo for FK
            # Mas como empresa/filial geralmente são IDs ou objetos, vamos tentar atribuir o ID direto se for campo ID,
            # ou buscar a instância se for FK.
            # Assumindo que o model espera uma instância de Empresas/Filiais, 
            # mas o Django aceita atribuição de ID no campo _id.
            
            # Verifica se o campo é uma FK
            try:
                field_obj = self.model._meta.get_field(self.empresa_field)
                if field_obj.is_relation:
                    setattr(self.object, f"{self.empresa_field}_id", empresa)
                else:
                    setattr(self.object, self.empresa_field, empresa)
            except:
                 setattr(self.object, self.empresa_field, empresa)

            try:
                field_obj = self.model._meta.get_field(self.filial_field)
                if field_obj.is_relation:
                     setattr(self.object, f"{self.filial_field}_id", filial)
                else:
                    setattr(self.object, self.filial_field, filial)
            except:
                setattr(self.object, self.filial_field, filial)

        self.object.save(using=db_name)
        form.save_m2m()
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'create'
        return context
