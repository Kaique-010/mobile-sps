from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import UpdateView

from Entidades.models import Entidades
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.forms import (
    MotoristaCadastroForm,
    MotoristaDadosComplementaresForm,
    MotoristaDocumentoFormSet,
    TranspMotoForm,
)
from transportes.services.transp_moto_sync_service import TranspMotoSyncService
from transportes.services.motorista_documento_status_service import MotoristaDocumentoStatusService
from transportes.models import MotoristaDadosComplementares, MotoristasCadastros, MotoristaDocumento


class TranspMotoUpdateView(UpdateView):
    model = Entidades
    form_class = TranspMotoForm
    template_name = 'transportes/transp_moto_form.html'
    context_object_name = 'entidade'

    def _get_banco(self):
        slug = self.kwargs.get('slug')
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_object(self, queryset=None):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        enti_clie = self.kwargs.get('enti_clie')
        return get_object_or_404(
            Entidades.objects.using(banco),
            enti_empr=empresa_id,
            enti_clie=enti_clie,
            enti_tien__in=['T', 'M'],
        )

    def _get_motorista_obj(self, banco, entidade):
        filial_id = self.request.session.get('filial_id') or 1
        return MotoristasCadastros.objects.using(banco).filter(
            empresa=entidade.enti_empr,
            filial=filial_id,
            entidade=entidade.enti_clie,
        ).first()

    def _build_forms(self, *, post_data=None):
        banco = self._get_banco()
        entidade = self.object
        is_post = post_data is not None

        motorista_obj = self._get_motorista_obj(banco, entidade) if entidade.enti_tien == 'M' else None
        dados_obj = None
        docs_qs = MotoristaDocumento.objects.none()

        if motorista_obj:
            dados_obj = MotoristaDadosComplementares.objects.using(banco).filter(
                empresa=entidade.enti_empr,
                filial=motorista_obj.filial,
                entidade=entidade.enti_clie,
            ).first()
            docs_qs = MotoristaDocumento.objects.using(banco).filter(
                empresa=entidade.enti_empr,
                filial=motorista_obj.filial,
                entidade=entidade.enti_clie,
            ).order_by('-criado_em')

        motorista_form = MotoristaCadastroForm(post_data if is_post else None, instance=motorista_obj, prefix='moto')
        dados_form = MotoristaDadosComplementaresForm(post_data if is_post else None, instance=dados_obj, prefix='dados')
        documentos_formset = MotoristaDocumentoFormSet(
            post_data if is_post else None,
            queryset=docs_qs,
            prefix='docs',
        )
        return motorista_form, dados_form, documentos_formset

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        banco = self._get_banco()
        empresa_id = request.session.get('empresa_id')
        filial_id = request.session.get('filial_id') or 1
        self._active_tab = (request.POST.get('active_tab') or '').strip() or None

        form = self.get_form()
        motorista_form, dados_form, documentos_formset = self._build_forms(post_data=request.POST)

        if not form.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    motorista_form=motorista_form,
                    dados_form=dados_form,
                    documentos_formset=documentos_formset,
                    active_tab=self._active_tab,
                )
            )

        self.object = form.save(commit=False)
        self.object.save(using=banco)

        if self.object.enti_tien == 'M':
            motorista = TranspMotoSyncService.sync_entidade_para_motorista(
                banco=banco,
                empresa_id=empresa_id,
                filial_id=filial_id,
                entidade_id=self.object.enti_clie,
            )

            if motorista is not None:
                motorista_form.instance = motorista
            if motorista_form.is_valid():
                cad = motorista_form.save(commit=False)
                cad.empresa = empresa_id
                cad.filial = filial_id
                cad.entidade = self.object.enti_clie
                cad.save(using=banco)
            else:
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        motorista_form=motorista_form,
                        dados_form=dados_form,
                        documentos_formset=documentos_formset,
                        active_tab=self._active_tab,
                    )
                )

            dados_existente = MotoristaDadosComplementares.objects.using(banco).filter(
                empresa=empresa_id,
                filial=filial_id,
                entidade=self.object.enti_clie,
            ).first()
            if dados_existente is not None:
                dados_form.instance = dados_existente
            if dados_form.is_valid():
                dados = dados_form.save(commit=False)
                dados.empresa = empresa_id
                dados.filial = filial_id
                dados.entidade = self.object.enti_clie
                dados.save(using=banco)
            else:
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        motorista_form=motorista_form,
                        dados_form=dados_form,
                        documentos_formset=documentos_formset,
                        active_tab=self._active_tab,
                    )
                )

            if documentos_formset.is_valid():
                for form_excluido in documentos_formset.deleted_forms:
                    if getattr(form_excluido, 'instance', None) is not None and form_excluido.instance.pk:
                        form_excluido.instance.delete(using=banco)
                documentos = documentos_formset.save(commit=False)
                for doc in documentos:
                    doc.empresa = empresa_id
                    doc.filial = filial_id
                    doc.entidade = self.object.enti_clie
                    doc.status = MotoristaDocumentoStatusService.calcular_status(doc)
                    doc.save(using=banco)
            else:
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        motorista_form=motorista_form,
                        dados_form=dados_form,
                        documentos_formset=documentos_formset,
                        active_tab=self._active_tab,
                    )
                )

        messages.success(request, 'Cadastro atualizado com sucesso.')
        return redirect(self.get_success_url())

    def get_success_url(self):
        url = reverse(
            'transportes:transportadoras_motoristas_editar',
            kwargs={'slug': self.kwargs['slug'], 'enti_clie': self.object.enti_clie},
        )
        if getattr(self, '_active_tab', None):
            url = f"{url}?tab={self._active_tab}"
        return url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('titulo', 'Editar Transportadora/Motorista')
        context['slug'] = self.kwargs.get('slug')
        context['is_motorista'] = self.object.enti_tien == 'M'
        context['active_tab'] = kwargs.get('active_tab') or self.request.GET.get('tab') or 'aba-entidade'

        if context['is_motorista']:
            banco = self._get_banco()
            empresa_id = self.request.session.get('empresa_id')
            filial_id = self.request.session.get('filial_id') or 1
            itens_vencidos = MotoristaDocumentoStatusService.listar_itens_alerta(
                banco=banco,
                empresa_id=empresa_id,
                entidade_id=self.object.enti_clie,
                filial_id=filial_id,
                status='vencido',
            )
            itens_vencendo = MotoristaDocumentoStatusService.listar_itens_alerta(
                banco=banco,
                empresa_id=empresa_id,
                entidade_id=self.object.enti_clie,
                filial_id=filial_id,
                status='vencendo',
            )
            context['alertas_motorista'] = {
                'vencidos': itens_vencidos,
                'vencendo': itens_vencendo,
                'total_vencidos': len(itens_vencidos),
                'total_vencendo': len(itens_vencendo),
            }

        if 'motorista_form' not in context or 'dados_form' not in context or 'documentos_formset' not in context:
            motorista_form, dados_form, documentos_formset = self._build_forms()
            context['motorista_form'] = motorista_form
            context['dados_form'] = dados_form
            context['documentos_formset'] = documentos_formset
        return context
