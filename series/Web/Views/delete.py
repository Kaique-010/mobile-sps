from django.views.generic import DeleteView
from django.urls import reverse
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from ...models import Series

class SeriesDeleteView(DeleteView):
    model = Series
    template_name = "series/confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get("slug")
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return Series.objects.using(self.db_alias).get(
            seri_empr=self.kwargs["seri_empr"],
            seri_codi=self.kwargs["seri_codi"],
        )

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete(using=self.db_alias)
        return redirect(f"/web/{self.slug}/series/")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.slug
        return ctx
