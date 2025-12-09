
from django.forms import formset_factory
from .forms import ServicososexternaForm


ServicososexternaFormSet = formset_factory(
    ServicososexternaForm,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=False,
)