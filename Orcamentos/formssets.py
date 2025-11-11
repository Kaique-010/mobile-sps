from django.forms import formset_factory
from .forms import ItensOrcamentoVendaForm

ItensOrcamentoFormSet = formset_factory(ItensOrcamentoVendaForm, extra=1)