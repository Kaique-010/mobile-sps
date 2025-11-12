from django.forms import formset_factory
from .forms import ItensOrcamentoVendaForm

# Formset com suporte a deleção e validação de mínimo
ItensOrcamentoFormSet = formset_factory(
    ItensOrcamentoVendaForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)