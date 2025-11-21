from django.forms import formset_factory, BaseFormSet
from .forms import ItensOrcamentoVendaForm
import logging


class ItensOrcamentoBaseFormSet(BaseFormSet):
    def clean(self):
        logger = logging.getLogger(__name__)
        if any(self.errors):
            logger.warning("[ItensOrcamentoBaseFormSet.clean] errors pre=%s", self.errors)
            return
        valid_forms = []
        for f in self.forms:
            cd = getattr(f, 'cleaned_data', {}) or {}
            logger.debug("[ItensOrcamentoBaseFormSet.clean] cd=%s", cd)
            if cd.get('DELETE'):
                continue
            if not cd:
                continue
            valid_forms.append(f)
            if not cd.get('iped_prod'):
                logger.warning("[ItensOrcamentoBaseFormSet.clean] iped_prod ausente")
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
                logger.warning("[ItensOrcamentoBaseFormSet.clean] quantidade inválida=%s", q)
                f.add_error('iped_quan', 'Quantidade deve ser maior que zero')
            if u < 0:
                logger.warning("[ItensOrcamentoBaseFormSet.clean] unitário inválido=%s", u)
                f.add_error('iped_unit', 'Preço unitário não pode ser negativo')
        if not valid_forms:
            logger.error("[ItensOrcamentoBaseFormSet.clean] nenhum item válido")
            from django import forms as django_forms
            raise django_forms.ValidationError('O orçamento precisa ter ao menos um item válido')
        logger.debug("[ItensOrcamentoBaseFormSet.clean] valid_forms=%s errors=%s", len(valid_forms), self.errors)


ItensOrcamentoFormSet = formset_factory(
    ItensOrcamentoVendaForm,
    formset=ItensOrcamentoBaseFormSet,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)