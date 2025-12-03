from django.views.generic import FormView
from django.contrib import messages
from core.utils import get_licenca_db_config
from django.urls import reverse
from django.http import HttpResponseRedirect
from controledevisitas.models import Controlevisita, ItensVisita
from ..forms import ItemVisitaForm, ControleVisitaForm


class RegistrarItemVisitaView(FormView):
    template_name = 'ControleDeVisitas/item_registrar.html'
    form_class = ItemVisitaForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.ctrl_id = kwargs.get('ctrl_id')
        self.db_alias = get_licenca_db_config(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['ctrl_id'] = self.ctrl_id
        return ctx

    def form_valid(self, form):
        dados = form.cleaned_data
        visita = Controlevisita.objects.using(self.db_alias).get(ctrl_id=self.ctrl_id)
        try:
            ItensVisita.objects.using(self.db_alias).create(
                item_empr=visita.ctrl_empresa,
                item_fili=visita.ctrl_filial.empr_empr if hasattr(visita.ctrl_filial, 'empr_empr') else visita.ctrl_filial_id,
                item_visita=visita,
                item_prod=dados['produto_codigo'],
                item_quan=dados['quantidade'],
                item_unit=dados.get('valor_unitario') or None,
                item_obse=dados.get('observacoes') or None,
            )
            messages.success(self.request, 'Item registrado com sucesso.')
        except Exception as e:
            messages.error(self.request, f'Falha ao registrar item: {e}')
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return f"/web/{self.slug}/controle-de-visitas/resumo/{self.ctrl_id}/"


class ControleVisitaCreateView(FormView):
    template_name = 'ControleDeVisitas/visita_criar.html'
    form_class = ControleVisitaForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or 1
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or 1
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        return ctx

    def form_valid(self, form):
        dados = form.cleaned_data
        from Entidades.models import Entidades
        from Licencas.models import Empresas, Filiais
        try:
            empresa = Empresas.objects.using(self.db_alias).get(empr_codi=int(self.empresa_id))
        except Exception:
            messages.error(self.request, 'Empresa inválida')
            return self.form_invalid(form)
        try:
            filial = Filiais.objects.using(self.db_alias).get(empr_empr=int(self.filial_id))
        except Exception:
            messages.error(self.request, 'Filial inválida')
            return self.form_invalid(form)
        try:
            cliente = Entidades.objects.using(self.db_alias).get(enti_clie=dados['ctrl_cliente_id'])
        except Exception:
            messages.error(self.request, 'Cliente inválido')
            return self.form_invalid(form)
        vendedor = None
        if dados.get('ctrl_vendedor_id'):
            try:
                vendedor = Entidades.objects.using(self.db_alias).get(enti_clie=dados['ctrl_vendedor_id'])
            except Exception:
                vendedor = None
        etapa = None
        if dados.get('ctrl_etapa_id'):
            from controledevisitas.models import Etapavisita
            try:
                etapa = Etapavisita.objects.using(self.db_alias).get(etap_id=dados['ctrl_etapa_id'])
            except Exception:
                etapa = None
        try:
            max_numero = Controlevisita.objects.using(self.db_alias).filter(
                ctrl_empresa=empresa,
                ctrl_filial=filial,
            ).aggregate_max('ctrl_numero') if hasattr(Controlevisita.objects.using(self.db_alias), 'aggregate_max') else None
        except Exception:
            max_numero = None
        if not max_numero:
            from django.db.models import Max
            max_numero = Controlevisita.objects.using(self.db_alias).filter(
                ctrl_empresa=empresa,
                ctrl_filial=filial,
            ).aggregate(Max('ctrl_numero')).get('ctrl_numero__max') or 0
        from django.db.models import Max
        max_id = Controlevisita.objects.using(self.db_alias).aggregate(Max('ctrl_id')).get('ctrl_id__max') or 0
        try:
            obj = Controlevisita.objects.using(self.db_alias).create(
                ctrl_id=int(max_id) + 1,
                ctrl_empresa=empresa,
                ctrl_filial=filial,
                ctrl_numero=int(max_numero) + 1,
                ctrl_cliente=cliente,
                ctrl_data=dados['ctrl_data'],
                ctrl_vendedor=vendedor,
                ctrl_etapa=etapa,
                ctrl_obse=dados.get('ctrl_obse') or None,
                ctrl_contato=dados.get('ctrl_contato') or None,
                ctrl_fone=dados.get('ctrl_fone') or None,
                ctrl_km_inic=dados.get('ctrl_km_inic') or None,
                ctrl_km_fina=dados.get('ctrl_km_fina') or None,
                ctrl_prox_visi=dados.get('ctrl_prox_visi') or None,
                ctrl_novo=(1 if dados.get('ctrl_novo') else 0),
                ctrl_base=(1 if dados.get('ctrl_base') else 0),
                ctrl_prop=(1 if dados.get('ctrl_prop') else 0),
                ctrl_leva=(1 if dados.get('ctrl_leva') else 0),
                ctrl_proj=dados.get('ctrl_proj') or None,
            )
            messages.success(self.request, 'Visita criada com sucesso.')
            self.created_id = obj.ctrl_id
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f'Falha ao criar visita: {e}')
            return self.form_invalid(form)

    def get_success_url(self):
        return f"/web/{self.slug}/controle-de-visitas/resumo/{getattr(self, 'created_id', '') or ''}/"


class ControleVisitaEditView(FormView):
    template_name = 'ControleDeVisitas/visita_editar.html'
    form_class = ControleVisitaForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.ctrl_id = kwargs.get('ctrl_id')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or 1
        self.filial_id = request.session.get('filial_id') or request.headers.get('X-Filial') or 1
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return Controlevisita.objects.using(self.db_alias).select_related('ctrl_cliente','ctrl_vendedor','ctrl_etapa').get(ctrl_id=self.ctrl_id)

    def get_initial(self):
        v = self.get_object()
        return {
            'ctrl_data': v.ctrl_data,
            'ctrl_cliente_id': getattr(getattr(v,'ctrl_cliente',None),'enti_clie',None),
            'ctrl_vendedor_id': getattr(getattr(v,'ctrl_vendedor',None),'enti_clie',None),
            'ctrl_etapa_id': getattr(getattr(v,'ctrl_etapa',None),'etap_id',None),
            'ctrl_contato': getattr(v,'ctrl_contato',None),
            'ctrl_fone': getattr(v,'ctrl_fone',None),
            'ctrl_obse': getattr(v,'ctrl_obse',None),
            'ctrl_prox_visi': getattr(v,'ctrl_prox_visi',None),
            'ctrl_km_inic': getattr(v,'ctrl_km_inic',None),
            'ctrl_km_fina': getattr(v,'ctrl_km_fina',None),
            'ctrl_novo': bool(getattr(v,'ctrl_novo',0)),
            'ctrl_base': bool(getattr(v,'ctrl_base',0)),
            'ctrl_prop': bool(getattr(v,'ctrl_prop',0)),
            'ctrl_leva': bool(getattr(v,'ctrl_leva',0)),
            'ctrl_proj': getattr(v,'ctrl_proj',None),
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        v = self.get_object()
        ctx['slug'] = self.slug
        ctx['visita'] = v
        return ctx

    def form_valid(self, form):
        dados = form.cleaned_data
        v = self.get_object()
        from Entidades.models import Entidades
        vendedor = None
        cliente = None
        etapa = None
        if dados.get('ctrl_cliente_id'):
            try:
                cliente = Entidades.objects.using(self.db_alias).get(enti_clie=dados['ctrl_cliente_id'])
            except Exception:
                cliente = None
        if dados.get('ctrl_vendedor_id'):
            try:
                vendedor = Entidades.objects.using(self.db_alias).get(enti_clie=dados['ctrl_vendedor_id'])
            except Exception:
                vendedor = None
        if dados.get('ctrl_etapa_id'):
            from controledevisitas.models import Etapavisita
            try:
                etapa = Etapavisita.objects.using(self.db_alias).get(etap_id=dados['ctrl_etapa_id'])
            except Exception:
                etapa = None
        try:
            v.ctrl_data = dados['ctrl_data']
            v.ctrl_cliente = cliente or v.ctrl_cliente
            v.ctrl_vendedor = vendedor or v.ctrl_vendedor
            v.ctrl_etapa = etapa or v.ctrl_etapa
            v.ctrl_contato = dados.get('ctrl_contato') or None
            v.ctrl_fone = dados.get('ctrl_fone') or None
            v.ctrl_obse = dados.get('ctrl_obse') or None
            v.ctrl_prox_visi = dados.get('ctrl_prox_visi') or None
            v.ctrl_km_inic = dados.get('ctrl_km_inic') or None
            v.ctrl_km_fina = dados.get('ctrl_km_fina') or None
            v.ctrl_novo = 1 if dados.get('ctrl_novo') else 0
            v.ctrl_base = 1 if dados.get('ctrl_base') else 0
            v.ctrl_prop = 1 if dados.get('ctrl_prop') else 0
            v.ctrl_leva = 1 if dados.get('ctrl_leva') else 0
            v.ctrl_proj = dados.get('ctrl_proj') or None
            v.save(using=self.db_alias)
            messages.success(self.request, 'Visita atualizada com sucesso.')
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f'Falha ao atualizar visita: {e}')
            return self.form_invalid(form)

    def get_success_url(self):
        return f"/web/{self.slug}/controle-de-visitas/resumo/{self.ctrl_id}/"
