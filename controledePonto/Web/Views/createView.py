from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView

from core.decorator import ModuloRequeridoMixin
from core.excecoes import ErroDominio
from controledePonto.Web.forms import RegistroPontoForm
from controledePonto.services import RegistroPontoService


class RegistroPontoCreateView(ModuloRequeridoMixin, FormView):
    modulo_requerido = 'controledePonto'
    template_name = 'controledePonto/registro_form.html'
    form_class = RegistroPontoForm

    def form_valid(self, form):
        service = RegistroPontoService(request=self.request)
        try:
            service.registrar(
                colaborador_id=form.cleaned_data['colaborador_id'],
                tipo=form.cleaned_data['tipo'],
            )
        except ErroDominio as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(self.request, 'Registro de ponto realizado com sucesso.')
        return redirect('controledePonto_web:registro_ponto_list')
