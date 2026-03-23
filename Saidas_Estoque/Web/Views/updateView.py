from django.views.generic import UpdateView
from django.shortcuts import redirect
from Saidas_Estoque.models import SaidasEstoque
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from ..forms import SaidasEstoqueForm
import logging
logger = logging.getLogger(__name__)


class SaidaUpdateView(UpdateView):
    model = SaidasEstoque
    form_class = SaidasEstoqueForm
    template_name = 'Saidas/saidas_criar.html'

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/saidas/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return SaidasEstoque.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        try:
            from Produtos.models import Lote
            from decimal import Decimal
            obj = form.save(commit=False)
            unit = form.cleaned_data.get('valor_unitario')
            if unit is not None and obj.said_quan is not None:
                obj.said_tota = obj.said_quan * unit
            obj.said_lote_vend = form.cleaned_data.get('said_lote_vend') or obj.said_lote_vend
            obj.save(using=banco)
            lote_num = obj.said_lote_vend
            if lote_num:
                try:
                    lote = Lote.objects.using(banco).filter(
                        lote_empr=int(obj.said_empr),
                        lote_prod=str(obj.said_prod),
                        lote_lote=int(lote_num),
                    ).first()
                    if lote:
                        if form.cleaned_data.get('lote_data_fabr'):
                            lote.lote_data_fabr = form.cleaned_data.get('lote_data_fabr')
                        if form.cleaned_data.get('lote_data_vali'):
                            lote.lote_data_vali = form.cleaned_data.get('lote_data_vali')
                        lote.save(using=banco)
                except Exception:
                    pass
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao atualizar saída: {e}")
            return self.form_invalid(form)
