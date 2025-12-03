from django.views.generic import ListView, FormView
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from core.utils import get_licenca_db_config
from django.db.models import Max
from controledevisitas.models import Etapavisita


class EtapaVisitaListView(ListView):
    template_name = 'ControleDeVisitas/etapas_list.html'
    context_object_name = 'etapas'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        try:
            self.empresa_id = int(request.session.get('empresa_id') or request.headers.get('X-Empresa') or 1)
        except Exception:
            self.empresa_id = 1
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Etapavisita.objects.using(self.db_alias).filter(etap_empr__empr_codi=self.empresa_id)
        descricao = (self.request.GET.get('descricao') or '').strip()
        if descricao:
            qs = qs.filter(etap_descricao__icontains=descricao)
        return qs.order_by('etap_nume')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['descricao'] = (self.request.GET.get('descricao') or '').strip()
        return ctx


class EtapaVisitaCreateView(FormView):
    template_name = 'ControleDeVisitas/etapa_form.html'
    from ..forms import EtapaVisitaForm
    form_class = EtapaVisitaForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        try:
            self.empresa_id = int(request.session.get('empresa_id') or request.headers.get('X-Empresa') or 1)
        except Exception:
            self.empresa_id = 1
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['modo'] = 'criar'
        return ctx

    def form_valid(self, form):
        cd = form.cleaned_data
        from Licencas.models import Empresas
        try:
            empresa = Empresas.objects.using(self.db_alias).get(empr_codi=self.empresa_id)
        except Exception:
            messages.error(self.request, 'Empresa inválida')
            return self.form_invalid(form)

        try:
            max_id = Etapavisita.objects.using(self.db_alias).aggregate(Max('etap_id')).get('etap_id__max') or 0
            novo_id = int(max_id) + 1
            max_nume = Etapavisita.objects.using(self.db_alias).filter(etap_empr=empresa).aggregate(Max('etap_nume')).get('etap_nume__max') or 0
            novo_nume = int(max_nume) + 1
            Etapavisita.objects.using(self.db_alias).create(
                etap_id=novo_id,
                etap_nume=novo_nume,
                etap_descricao=cd.get('etap_descricao') or None,
                etap_empr=empresa,
                etap_obse=cd.get('etap_obse') or None,
            )
            messages.success(self.request, 'Etapa criada com sucesso.')
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f'Falha ao criar etapa: {e}')
            return self.form_invalid(form)

    def get_success_url(self):
        return f"/web/{self.slug}/controle-de-visitas/etapas/"


class EtapaVisitaUpdateView(FormView):
    template_name = 'ControleDeVisitas/etapa_form.html'
    from ..forms import EtapaVisitaForm
    form_class = EtapaVisitaForm

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.etap_id = kwargs.get('etap_id')
        self.db_alias = get_licenca_db_config(request)
        try:
            self.empresa_id = int(request.session.get('empresa_id') or request.headers.get('X-Empresa') or 1)
        except Exception:
            self.empresa_id = 1
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return Etapavisita.objects.using(self.db_alias).select_related('etap_empr').get(etap_id=self.etap_id, etap_empr__empr_codi=self.empresa_id)

    def get_initial(self):
        o = self.get_object()
        return {
            'etap_nume': getattr(o, 'etap_nume', None),
            'etap_descricao': getattr(o, 'etap_descricao', None),
            'etap_obse': getattr(o, 'etap_obse', None),
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['slug'] = self.slug
        ctx['modo'] = 'editar'
        return ctx

    def form_valid(self, form):
        cd = form.cleaned_data
        o = self.get_object()
        try:
            # Número da etapa é imutável para manter sequência; não atualizamos o campo
            o.etap_descricao = cd.get('etap_descricao') or None
            o.etap_obse = cd.get('etap_obse') or None
            o.save(using=self.db_alias)
            messages.success(self.request, 'Etapa atualizada com sucesso.')
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f'Falha ao atualizar etapa: {e}')
            return self.form_invalid(form)

    def get_success_url(self):
        return f"/web/{self.slug}/controle-de-visitas/etapas/"


class EtapaVisitaDeleteView(View):
    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.etap_id = kwargs.get('etap_id')
        self.db_alias = get_licenca_db_config(request)
        try:
            self.empresa_id = int(request.session.get('empresa_id') or request.headers.get('X-Empresa') or 1)
        except Exception:
            self.empresa_id = 1
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            obj = Etapavisita.objects.using(self.db_alias).get(etap_id=self.etap_id, etap_empr__empr_codi=self.empresa_id)
            obj.delete(using=self.db_alias)
            messages.success(request, 'Etapa excluída com sucesso.')
        except Exception as e:
            messages.error(request, f'Falha ao excluir etapa: {e}')
        return redirect(f"/web/{self.slug}/controle-de-visitas/etapas/")

