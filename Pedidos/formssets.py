
from django.forms import formset_factory
from .forms import ItensPedidoVendaForm

# Formset simples (não vinculado a FK)
ItensPedidoFormSet = formset_factory(
    ItensPedidoVendaForm,
    extra=0,  # Começa com 1 linha
    can_delete=True,
    min_num=1,  # Mínimo 1 item
    validate_min=True,
)