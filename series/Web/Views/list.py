from django.views.generic import ListView
from core.utils import get_licenca_db_config
from ...models import Series

class SeriesListView(ListView):
    model = Series
    template_name = "series/list.html"
    context_object_name = "series"
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get("slug")
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get("empresa_id")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Series.objects.using(self.db_alias).filter(seri_empr=self.empresa_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slug"] = self.slug
        return context
