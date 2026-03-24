from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django import forms
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.db import transaction

from core.utils import get_licenca_db_config
from transportes.models import Cte
from transportes.forms.emissao import CteEmissaoForm
from transportes.forms.tipo import CteTipoForm
from transportes.forms.rota import CteRotaForm
from transportes.forms.seguro import CteSeguroForm
from transportes.forms.carga import CteCargaForm
from transportes.forms.tributacao import CteTributacaoForm
from transportes.forms.documento import CteDocumentoFormSet
from transportes.services.rascunho_service import RascunhoService
from transportes.services.emissao_service import EmissaoService
from transportes.services.sefaz_gateway import SefazGateway
from transportes.services.numeracao_service import NumeracaoService
from Entidades.models import Entidades
from transportes.models import Veiculos

import logging

logger = logging.getLogger(__name__)

class CteBaseMixin(LoginRequiredMixin):
    login_url = reverse_lazy('web_login')

    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        # Filtra registros inválidos que possam ter id vazio ou nulo (legado)
        return Cte.objects.using(slug).exclude(id__exact='').exclude(id__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = get_licenca_db_config(self.request)
        # Garante que active_tab esteja no contexto mesmo para CreateView (onde self.object é None)
        context['active_tab'] = getattr(self, 'active_tab', 'emissao')
        return context

class CteListView(CteBaseMixin, ListView):
    model = Cte
    template_name = 'transportes/cte_list.html'
    context_object_name = 'ctes'
    ordering = ['-id']
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = get_licenca_db_config(self.request)
        ctes_pagina = context['ctes']
        qs_total = self.get_queryset()

        context['total_ctes'] = qs_total.count()
        context['total_autorizados'] = qs_total.filter(status='AUT').count()
        context['total_emitidos'] = (
            qs_total.exclude(status='RAS')
            .exclude(status__isnull=True)
            .exclude(status='')
            .count()
        )

        class EntidadeDisplay:
            def __init__(self, nome):
                self.nome = nome
            def __str__(self):
                return self.nome

        remetentes_ids = list(
            qs_total.exclude(remetente__isnull=True).values_list('remetente', flat=True)
        )
        destinatarios_ids = [
            cte.destinatario for cte in ctes_pagina
            if getattr(cte, 'destinatario', None)
        ]

        ids_entidades = set(remetentes_ids) | set(
            cte.remetente for cte in ctes_pagina
            if getattr(cte, 'remetente', None)
        ) | set(destinatarios_ids)

        nomes_entidades = {}
        if ids_entidades:
            entidades = (
                Entidades.objects.using(slug)
                .filter(enti_clie__in=ids_entidades)
                .values('enti_clie', 'enti_nome')
            )
            for ent in entidades:
                nomes_entidades[ent['enti_clie']] = ent['enti_nome']

        total_por_remetente = {}
        for remetente_id in remetentes_ids:
            total_por_remetente[remetente_id] = total_por_remetente.get(remetente_id, 0) + 1

        total_por_remetente_display = {}
        for remetente_id, total in total_por_remetente.items():
            nome = nomes_entidades.get(remetente_id, str(remetente_id))
            total_por_remetente_display[EntidadeDisplay(nome)] = total
        context['total_por_remetente'] = total_por_remetente_display

        for cte in ctes_pagina:
            if getattr(cte, 'remetente', None):
                nome = nomes_entidades.get(cte.remetente, str(cte.remetente))
                cte.remetente = EntidadeDisplay(nome)
            if getattr(cte, 'destinatario', None):
                nome = nomes_entidades.get(cte.destinatario, str(cte.destinatario))
                cte.destinatario = EntidadeDisplay(nome)

        return context

class CteCreateView(CteBaseMixin, CreateView):
    model = Cte
    form_class = CteEmissaoForm
    template_name = 'transportes/cte_form.html'
    active_tab = 'emissao'

    def form_valid(self, form):
        try:
            slug = get_licenca_db_config(self.request)
            
            # Recupera empresa e filial da sessão
            empresa_id = self.request.session.get('empresa_id')
            filial_id = self.request.session.get('filial_id')

            if not empresa_id:
                raise ValueError("Empresa não encontrada na sessão.")
            
            self.object = form.save(commit=False)
            
            # Define campos obrigatórios do sistema
            self.object.empresa = empresa_id
            self.object.filial = filial_id or 1  # Default para 1 se não houver filial
            self.object.status = 'RAS' # Garante status rascunho
            
            # Campos padrão obrigatórios para CTe
            self.object.modelo = '57'
            self.object.serie = '1'

            # Gera número sequencial e define ID igual ao número
            service = NumeracaoService(empresa_id, self.object.filial, self.object.serie, slug)
            prox_num = service.proximo_numero()
            
            self.object.id = str(prox_num)
            self.object.numero = prox_num
            
            # Preencher campos de auditoria/sistema se necessário
            self.object.save(using=slug)
            
            messages.success(self.request, "CT-e criado com sucesso! Continue preenchendo as abas.")
            # Redireciona para a mesma aba (emissao) mas agora editando o objeto criado
            return HttpResponseRedirect(reverse('transportes:cte_emissao', kwargs={'slug': slug, 'pk': self.object.pk}))
        except Exception as e:
            logger.error(f"Erro ao criar CTe: {e}")
            messages.error(self.request, f"Erro ao criar CT-e: {e}")
            return self.form_invalid(form)

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_emissao', kwargs={'slug': slug, 'pk': self.object.pk})

class CteUpdateBaseView(CteBaseMixin, UpdateView):
    model = Cte
    template_name = 'transportes/cte_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        slug = get_licenca_db_config(self.request)
        try:
            self.object = form.save(commit=False)
            self.object.save(using=slug)
            messages.success(self.request, "Dados salvos com sucesso!")
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            messages.error(self.request, f"Erro ao salvar: {e}")
            return self.form_invalid(form)

class CteEmissaoView(CteUpdateBaseView):
    form_class = CteEmissaoForm
    active_tab = 'emissao'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = get_licenca_db_config(self.request)
        
        if self.object:
            # Remetente
            if self.object.remetente:
                try:
                    remetente = Entidades.objects.using(slug).get(enti_clie=self.object.remetente)
                    context['remetente_nome'] = f"{remetente.enti_clie} - {remetente.enti_nome}"
                except Entidades.DoesNotExist:
                    pass
            
            # Destinatário
            if self.object.destinatario:
                try:
                    destinatario = Entidades.objects.using(slug).get(enti_clie=self.object.destinatario)
                    context['destinatario_nome'] = f"{destinatario.enti_clie} - {destinatario.enti_nome}"
                except Entidades.DoesNotExist:
                    pass

            # Motorista
            if self.object.motorista:
                try:
                    motorista = Entidades.objects.using(slug).get(enti_clie=self.object.motorista)
                    context['motorista_nome'] = f"{motorista.enti_clie} - {motorista.enti_nome}"
                except Entidades.DoesNotExist:
                    pass

            # Veículo
            if self.object.veiculo:
                try:
                    # Veículo usa chave composta, mas CTe guarda apenas um ID (sequencial?)
                    # Na verdade, CTe guarda cte_veic que parece ser o sequencial.
                    # Mas para buscar o veículo único, precisamos de empresa e transportadora também.
                    # O CTe tem transportadora (cte_tran). A empresa está na sessão ou no próprio CTe (cte_empr).
                    # Assumindo que o veículo pertence à transportadora do CTe.
                    
                    # Se cte_tran estiver preenchido (que deve ser o remetente se for CTe normal?)
                    # O CTe tem campo 'transportadora' (cte_tran).
                    
                    empresa_id = self.request.session.get('empresa_id')
                    transportadora_id = self.object.transportadora or self.object.remetente # Fallback?
                    
                    if transportadora_id:
                         veiculo = Veiculos.objects.using(slug).filter(
                             veic_empr=empresa_id,
                             veic_tran=transportadora_id,
                             veic_sequ=self.object.veiculo
                         ).first()
                         
                         if veiculo:
                             context['veiculo_nome'] = f"{veiculo.veic_plac} - {veiculo.veic_marc or ''}"
                except Exception:
                    pass
                    
        return context

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_tipo', kwargs={'slug': slug, 'pk': self.object.pk})

class CteTipoView(CteUpdateBaseView):
    form_class = CteTipoForm
    active_tab = 'tipo'

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_rota', kwargs={'slug': slug, 'pk': self.object.pk})

class CteRotaView(CteUpdateBaseView):
    form_class = CteRotaForm
    active_tab = 'rota'

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_seguro', kwargs={'slug': slug, 'pk': self.object.pk})

class CteSeguroView(CteUpdateBaseView):
    form_class = CteSeguroForm
    active_tab = 'seguro'

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_carga', kwargs={'slug': slug, 'pk': self.object.pk})

class CteCargaView(CteUpdateBaseView):
    form_class = CteCargaForm
    active_tab = 'carga'

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_tributacao', kwargs={'slug': slug, 'pk': self.object.pk})

class CteTributacaoView(CteUpdateBaseView):
    form_class = CteTributacaoForm
    template_name = 'transportes/cte_tributacao.html'
    active_tab = 'tributacao'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        # Permanece na mesma tela para conferência dos cálculos
        slug = get_licenca_db_config(self.request)
        messages.success(self.request, "Tributação salva e calculada com sucesso!")
        return reverse('transportes:cte_tributacao', kwargs={'slug': slug, 'pk': self.object.pk})

class CteDocumentoView(CteUpdateBaseView):
    # Usa um form vazio para o CTE, pois só vamos mexer nos documentos
    form_class = forms.modelform_factory(Cte, fields=[]) 
    template_name = 'transportes/cte_form.html'
    active_tab = 'documentos'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'request' in kwargs:
            del kwargs['request']
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = get_licenca_db_config(self.request)
        if self.request.POST:
            context['documentos_formset'] = CteDocumentoFormSet(self.request.POST, instance=self.object, queryset=self.object.documentos.using(slug).all())
        else:
            context['documentos_formset'] = CteDocumentoFormSet(instance=self.object, queryset=self.object.documentos.using(slug).all())
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['documentos_formset']
        slug = get_licenca_db_config(self.request)
        
        if formset.is_valid():
            # Não precisa salvar o form do CTE se estiver vazio, mas mal não faz
            # self.object = form.save(commit=False)
            # self.object.save(using=slug)
            
            # Save formset with the correct database alias
            instances = formset.save(commit=False)
            for instance in instances:
                instance.cte = self.object
                instance.save(using=slug)
            
            for obj in formset.deleted_objects:
                obj.delete(using=slug)
                
            messages.success(self.request, "Documentos salvos com sucesso!")
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.error(self.request, "Erro ao salvar documentos. Verifique os campos.")
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_documento', kwargs={'slug': slug, 'pk': self.object.pk})

class CteDeleteView(CteBaseMixin, DeleteView):
    model = Cte
    template_name = 'transportes/cte_confirm_delete.html'

    def get_success_url(self):
        slug = get_licenca_db_config(self.request)
        return reverse('transportes:cte_list', kwargs={'slug': slug})

    def delete(self, request, *args, **kwargs):
        slug = get_licenca_db_config(self.request)
        self.object = self.get_object()
        if self.object.status not in ['RAS', 'REJ', 'ERR']:
            messages.error(request, "Apenas CT-e em Rascunho, Rejeitado ou Erro podem ser excluídos.")
            return HttpResponseRedirect(self.get_success_url())
        
        try:
            self.object.delete(using=slug)
            messages.success(request, "CT-e excluído com sucesso.")
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            messages.error(request, f"Erro ao excluir: {e}")
            return HttpResponseRedirect(self.get_success_url())

class CteEmitirView(CteBaseMixin, View):
    def post(self, request, pk, slug=None):
        slug = get_licenca_db_config(request)
        cte = get_object_or_404(Cte.objects.using(slug), pk=pk)
        success_url = reverse('transportes:cte_list', kwargs={'slug': slug})
        
        try:
            # Chama service direto (síncrono) - Removido Celery/Shared Task
            service = EmissaoService(cte, slug=slug)
            resultado = service.emitir()
            
            status_emissao = resultado.get('status')
            mensagem_sefaz = resultado.get('mensagem', '')
            
            if status_emissao == 'autorizado':
                messages.success(request, f"CT-e Autorizado! Protocolo: {resultado.get('protocolo')}")
            elif status_emissao == 'recebido':
                messages.info(request, f"CT-e Recebido em processamento. Recibo: {resultado.get('recibo')}")
            elif status_emissao == 'rejeitado':
                messages.error(request, f"CT-e Rejeitado: {mensagem_sefaz}")
            else:
                messages.warning(request, f"Status: {status_emissao}. Msg: {mensagem_sefaz}")
            
            return HttpResponseRedirect(success_url)
            
        except Exception as e:
            logger.error(f"Erro na emissão do CTe {pk}: {e}")
            messages.error(request, f"Erro ao emitir: {e}")
            return HttpResponseRedirect(success_url)

from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from brazilfiscalreport.dacte.dacte import Dacte
from lxml import etree
import io

class CteImprimirDacteView(CteBaseMixin, View):
    def get(self, request, pk, slug=None):
        slug = get_licenca_db_config(request)
        cte = get_object_or_404(Cte.objects.using(slug), pk=pk)
        
        if not cte.xml_cte:
            messages.error(request, "CT-e não possui XML autorizado para impressão.")
            return HttpResponseRedirect(reverse('transportes:cte_list', kwargs={'slug': slug}))
            
        try:
            # Parse do XML
            xml_content = cte.xml_cte
            # Se for string, converte para bytes
            if isinstance(xml_content, str):
                xml_content = xml_content.encode('utf-8')
                
            # Gera DACTE
            dacte = Dacte(xml_content)
            
            # output(dest='S') retorna string/bytes do PDF
            # Em versoes mais novas do fpdf/pyfpdf pode retornar bytearray ou string
            pdf_content = dacte.output(dest='S')
            
            if isinstance(pdf_content, str):
                pdf_content = pdf_content.encode('latin-1') # PDF binary safe encoding
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="cte-{cte.numero}.pdf"'
            return response
            
        except Exception as e:
            logger.error(f"Erro ao gerar DACTE para CTe {pk}: {e}")
            messages.error(request, f"Erro ao gerar PDF: {e}")
            return HttpResponseRedirect(reverse('transportes:cte_list', kwargs={'slug': slug}))

class CteConsultarReciboView(CteBaseMixin, View):
    def post(self, request, pk, slug=None): # slug=None para compatibilidade com URL
        slug = get_licenca_db_config(request)
        cte = get_object_or_404(Cte.objects.using(slug), pk=pk)
        success_url = reverse('transportes:cte_list', kwargs={'slug': slug})
        
        try:
            gateway = SefazGateway(cte)
            resultado = None
            
            # Prioriza consulta por recibo se existir
            if cte.recibo:
                try:
                    resultado = gateway.consultar_recibo(cte.recibo)
                except Exception as e:
                    logger.warning(f"Falha na consulta por recibo, tentando por chave: {e}")
                    # Se falhar recibo, tenta chave se disponível
            
            # Se não tiver recibo ou falhou, tenta por chave
            if not resultado and cte.chave:
                resultado = gateway.consultar_chave(cte.chave)
            
            if not resultado:
                 messages.warning(request, "CT-e não possui recibo nem chave para consulta.")
                 return HttpResponseRedirect(success_url)

            status_consulta = resultado.get('status')
            mensagem = resultado.get('mensagem', '')
            
            if status_consulta == 'autorizado':
                cte.protocolo = resultado.get('protocolo')
                cte.status = 'AUT'
                # Atualiza XML se veio na consulta
                if resultado.get('xml_protocolo'):
                     # Se já tem XML assinado, tenta montar o procCTe
                     xml_protocolo = resultado.get('xml_protocolo')
                     
                     # Verifica se cte.xml_cte existe e se já não é um procCTe
                     if cte.xml_cte:
                         # Se for bytes, decode
                         xml_assinado = cte.xml_cte
                         if isinstance(xml_assinado, bytes):
                             xml_assinado = xml_assinado.decode('utf-8')
                             
                         # Se ainda não tem protCTe (não é distribuição)
                         if 'protCTe' not in xml_assinado:
                             try:
                                 # Remove declaração XML e limpa string
                                 if '<?xml' in xml_assinado:
                                     xml_assinado = xml_assinado.split('?>', 1)[-1].strip()
                                     
                                 # Remove declaração do protocolo também se existir
                                 if '<?xml' in xml_protocolo:
                                     xml_protocolo = xml_protocolo.split('?>', 1)[-1].strip()

                                 # Monta procCTe manualmente para garantir estrutura de distribuição
                                 proc_cte = f'<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">{xml_assinado}{xml_protocolo}</cteProc>'
                                 
                                 cte.xml_cte = proc_cte
                             except Exception as e:
                                 logger.error(f"Erro ao montar procCTe na consulta: {e}")
                                 # Salva pelo menos o protocolo se falhar a montagem? 
                                 # Melhor não alterar se falhar para não corromper.
                     
                cte.save(using=slug)
                messages.success(request, f"CT-e Autorizado! Protocolo: {cte.protocolo}")
            elif status_consulta == 'rejeitado':
                cte.status = 'REJ'
                cte.observacoes_fiscais = f"Rejeição: {mensagem}"
                cte.save(using=slug)
                messages.error(request, f"CT-e Rejeitado: {mensagem}")
            elif status_consulta == 'processando':
                cte.status = 'PRO'
                if mensagem:
                    cte.observacoes_fiscais = mensagem
                cte.save(using=slug)
                messages.info(request, f"CT-e ainda em processamento: {mensagem}")
            elif status_consulta == 'recebido':
                cte.status = 'REC'
                if resultado.get('recibo'):
                    cte.recibo = resultado.get('recibo')
                if mensagem:
                    cte.observacoes_fiscais = mensagem
                cte.save(using=slug)
                messages.info(request, f"Lote Recebido. Aguardando processamento. Recibo: {resultado.get('recibo')}")
            else:
                if mensagem:
                    cte.observacoes_fiscais = mensagem
                    cte.save(using=slug)
                messages.warning(request, f"Status: {status_consulta}. Msg: {mensagem}")
                
        except Exception as e:
            logger.error(f"Erro ao consultar recibo/chave CTe {pk}: {e}")
            messages.error(request, f"Erro ao consultar: {e}")
        
        return HttpResponseRedirect(success_url)
