from django.forms import formset_factory
from .forms import ItensPedidoVendaForm

ItensPedidoFormSet = formset_factory(
    ItensPedidoVendaForm,
    extra=1,
    can_delete=True
)
