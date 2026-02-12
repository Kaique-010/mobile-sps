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

        # cria instância sem salvar
        self.object = form.save(commit=False)

        if self.empresa_field and self.filial_field:
            empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
            filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)

            setattr(self.object, self.empresa_field, empresa)
            setattr(self.object, self.filial_field, filial)

        # agora delega
        self.object = self.execute_create(form, db_name)

        return redirect(self.get_success_url())

    def execute_create(self, form, db_name):
        # usa self.object já montado
        self.object.save(using=db_name)
        form.save_m2m()
        return self.object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'create'
        return context
