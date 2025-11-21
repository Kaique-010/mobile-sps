
from django import forms
from django.forms import formset_factory, BaseFormSet
from .forms import ItensPedidoVendaForm
import logging

class ItensPedidoBaseFormSet(BaseFormSet):
    def clean(self):
        logger = logging.getLogger(__name__)
        if any(self.errors):
            logger.warning("[ItensPedidoBaseFormSet.clean] errors pre=%s", self.errors)
            return
        valid_forms = []
        for f in self.forms:
            cd = getattr(f, 'cleaned_data', {}) or {}
            logger.debug("[ItensPedidoBaseFormSet.clean] cd=%s", cd)
            if cd.get('DELETE'):
                continue
            if not cd:
                continue
            valid_forms.append(f)
            if not cd.get('iped_prod'):
                logger.warning("[ItensPedidoBaseFormSet.clean] iped_prod ausente")
                f.add_error('iped_prod', 'Produto é obrigatório')
            try:
                q = cd.get('iped_quan') or 0
            except Exception:
                q = 0
            try:
                u = cd.get('iped_unit') or 0
            except Exception:
                u = 0
            if q <= 0:
                logger.warning("[ItensPedidoBaseFormSet.clean] quantidade inválida=%s", q)
                f.add_error('iped_quan', 'Quantidade deve ser maior que zero')
            if u < 0:
                logger.warning("[ItensPedidoBaseFormSet.clean] unitário inválido=%s", u)
                f.add_error('iped_unit', 'Preço unitário não pode ser negativo')
        if not valid_forms:
            logger.error("[ItensPedidoBaseFormSet.clean] nenhum item válido")
            raise forms.ValidationError('O pedido precisa ter ao menos um item válido')
        logger.debug("[ItensPedidoBaseFormSet.clean] valid_forms=%s errors=%s", len(valid_forms), self.errors)

ItensPedidoFormSet = formset_factory(
    ItensPedidoVendaForm,
    formset=ItensPedidoBaseFormSet,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)