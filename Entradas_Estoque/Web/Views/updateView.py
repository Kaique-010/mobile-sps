from django.views.generic import  UpdateView
import logging
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug
from django.shortcuts import redirect
logger = logging.getLogger(__name__)
from ...models import EntradaEstoque
from ..forms import EntradaEstoqueForm



class EntradaUpdateView(UpdateView):
    model = EntradaEstoque
    form_class = EntradaEstoqueForm
    template_name = 'Entradas/entradas_criar.html'

    def get_initial(self):
        initial = super().get_initial()
        banco = get_licenca_db_config(self.request) or 'default'
        obj = self.get_object()
        try:
            from Produtos.models import Lote, Tabelaprecos

            prod_raw = str(getattr(obj, 'entr_prod', '') or '').strip()
            prod_variants = []
            if prod_raw:
                prod_variants.append(prod_raw)
                if prod_raw.isdigit():
                    prod_variants.append(prod_raw.zfill(6))
                    prod_variants.append(str(int(prod_raw)))
            prod_variants = [p for i, p in enumerate(prod_variants) if p and p not in prod_variants[:i]]

            lote_num = getattr(obj, 'entr_lote_vend', None)
            if lote_num:
                lote = (
                    Lote.objects.using(banco)
                    .filter(
                        lote_empr=int(obj.entr_empr),
                        lote_prod__in=prod_variants or [prod_raw],
                        lote_lote=int(lote_num),
                    )
                    .first()
                )
                if lote:
                    if getattr(lote, 'lote_data_fabr', None):
                        initial['lote_data_fabr'] = lote.lote_data_fabr
                    if getattr(lote, 'lote_data_vali', None):
                        initial['lote_data_vali'] = lote.lote_data_vali

            preco = (
                Tabelaprecos.objects.using(banco)
                .filter(
                    tabe_empr=int(obj.entr_empr),
                    tabe_fili=int(obj.entr_fili),
                    tabe_prod__in=prod_variants or [prod_raw],
                )
                .first()
            )
            if preco:
                if getattr(preco, 'tabe_avis', None) is not None:
                    initial['preco_vista'] = preco.tabe_avis
                if getattr(preco, 'tabe_apra', None) is not None:
                    initial['preco_prazo'] = preco.tabe_apra
        except Exception:
            pass

        if 'atualizar_preco' not in initial:
            initial['atualizar_preco'] = True
        if 'auto_lote' not in initial:
            initial['auto_lote'] = False
        return initial

    def get_success_url(self):
        slug = self.kwargs.get('slug')
        return f"/web/{slug}/entradas/" if slug else "/web/home/"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['database'] = get_licenca_db_config(self.request) or 'default'
        kwargs['empresa_id'] = self.request.session.get('empresa_id', 1)
        return kwargs

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        return EntradaEstoque.objects.using(banco).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        context['slug'] = self.kwargs.get('slug') or get_licenca_slug()
        return context

    def form_valid(self, form):
        banco = get_licenca_db_config(self.request) or 'default'
        try:
            from Produtos.models import Lote, Tabelaprecos
            from decimal import Decimal
            obj = form.save(commit=False)
            obj.entr_lote_vend = form.cleaned_data.get('entr_lote_vend') or obj.entr_lote_vend
            obj.save(using=banco)
            lote_num = obj.entr_lote_vend
            if lote_num:
                try:
                    lote = Lote.objects.using(banco).filter(
                        lote_empr=int(obj.entr_empr),
                        lote_prod=str(obj.entr_prod),
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

            if bool(form.cleaned_data.get('atualizar_preco')):
                preco_vista = form.cleaned_data.get('preco_vista')
                preco_prazo = form.cleaned_data.get('preco_prazo')
                update_fields = {
                    'tabe_cuge': Decimal(str(obj.entr_unit or 0)).quantize(Decimal('0.01')),
                    'tabe_entr': obj.entr_data,
                }
                if preco_vista is not None:
                    update_fields['tabe_avis'] = Decimal(str(preco_vista)).quantize(Decimal('0.01'))
                if preco_prazo is not None:
                    update_fields['tabe_apra'] = Decimal(str(preco_prazo)).quantize(Decimal('0.01'))
                qs = Tabelaprecos.objects.using(banco).filter(
                    tabe_empr=int(obj.entr_empr),
                    tabe_fili=int(obj.entr_fili),
                    tabe_prod=str(obj.entr_prod),
                )
                updated = qs.update(**update_fields)
                if not updated:
                    create_fields = {
                        'tabe_empr': int(obj.entr_empr),
                        'tabe_fili': int(obj.entr_fili),
                        'tabe_prod': str(obj.entr_prod),
                        **update_fields,
                    }
                    Tabelaprecos.objects.using(banco).create(**create_fields)
            return redirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao atualizar entrada: {e}")
            return self.form_invalid(form)
