
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

TabelaprecosFormSet = forms.modelformset_factory(
    Tabelaprecos,
    form=TabelaprecosForm,
    extra=1,
)

# Formset simples (sem PK/id oculto), usado para POST seguro
TabelaprecosPlainFormSet = formset_factory(
    TabelaprecosForm,
    extra=0,
)