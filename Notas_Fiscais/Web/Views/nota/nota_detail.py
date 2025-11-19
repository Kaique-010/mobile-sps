# notas_fiscais/views/nota/nota_detail.py

from django.views.generic import DetailView
from ....models import Nota


class NotaDetailView(DetailView):
    model = Nota
    template_name = "notas/nota_detail.html"
    context_object_name = "nota"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["slug"] = self.kwargs.get("slug")
        return ctx
