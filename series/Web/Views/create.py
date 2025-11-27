from django.urls import reverse
from django.views.generic import CreateView
from core.utils import get_licenca_db_config
from ...models import Series
from ..form import SeriesForm

class SeriesCreateView(CreateView):
    model = Series
    template_name = "series/form.html"
    form_class = SeriesForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get("slug")
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or request.GET.get('filial')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.seri_empr = str(self.empresa_id) if self.empresa_id is not None else obj.seri_empr
        obj.seri_fili = str(self.filial_id) if self.filial_id is not None else obj.seri_fili
        obj.save(using=self.db_alias)
        return super().form_valid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa_id'] = self.empresa_id
        kwargs['filial_id'] = self.filial_id
        return kwargs

    def get_success_url(self):
        return f"/web/{self.slug}/series/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.slug
        return ctx
