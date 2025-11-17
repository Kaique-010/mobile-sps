
from django.forms import formset_factory
from .forms import PecasOsForm, ServicosOsForm

# Formset simples (não vinculado a FK)
PecasOsFormSet = formset_factory(
    PecasOsForm,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
ServicoOsFormSet = formset_factory(
    ServicosOsForm,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=False,
)