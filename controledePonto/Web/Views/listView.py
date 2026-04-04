from django.views.generic import TemplateView

from core.decorator import ModuloRequeridoMixin
from controledePonto.services import RegistroPontoService


class RegistroPontoListView(ModuloRequeridoMixin, TemplateView):
    modulo_requerido = 'controledePonto'
    template_name = 'controledePonto/registro_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        colaborador_id = self.request.GET.get('colaborador_id')
        service = RegistroPontoService(request=self.request)
        registros = service.listar(colaborador_id=int(colaborador_id)) if colaborador_id else service.listar()

        context['registros'] = registros
        context['filtro_colaborador_id'] = colaborador_id or ''
        return context
