from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
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
from transportes.services.rascunho_service import RascunhoService
from transportes.services.emissao_service import EmissaoService
from Entidades.models import Entidades
from transportes.models import Veiculos

import logging

logger = logging.getLogger(__name__)

class CteBaseMixin(LoginRequiredMixin):
    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        # Filtra registros inválidos que possam ter id vazio ou nulo (legado)
        return Cte.objects.using(slug).exclude(id__exact='').exclude(id__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = get_licenca_db_config(self.request)
        if hasattr(self, 'object') and self.object:
            context['active_tab'] = self.active_tab if hasattr(self, 'active_tab') else 'emissao'
        return context

class CteListView(CteBaseMixin, ListView):
    model = Cte
    template_name = 'transportes/cte_list.html'
    context_object_name = 'ctes'
    ordering = ['-id']
    paginate_by = 20

class CteCreateView(CteBaseMixin, CreateView):
    model = Cte
    form_class = CteEmissaoForm
    template_name = 'transportes/cte_form.html'
    active_tab = 'emissao'

    def form_valid(self, form):
        try:
            slug = get_licenca_db_config(self.request)
            service = RascunhoService(
                empresa=None, # Será obtido via contexto ou request
                filial=None,  # Será obtido via contexto ou request
                user=self.request.user,
                slug=slug
            )
            # O service cria o rascunho. O form.save() padrão do Django não usa o service diretamente,
            # mas aqui podemos interceptar para usar o service se quisermos,
            # ou deixar o form salvar e o service apenas gerenciar regras extras.
            # Como o RascunhoService encapsula lógica de criação inicial (status, etc),
            # vamos usar o form para validar e o service para criar se necessário,
            # mas para simplicidade no Django Forms, vamos deixar o form salvar e ajustar o objeto.
            
            self.object = form.save(commit=False)
            self.object.status = 'RAS' # Garante status rascunho
            # Preencher campos de auditoria/sistema se necessário
            self.object.save(using=slug)
            
            messages.success(self.request, "CT-e criado com sucesso! Continue preenchendo as abas.")
            return HttpResponseRedirect(self.get_success_url())
        except Exception as e:
            logger.error(f"Erro ao criar CTe: {e}")
            messages.error(self.request, f"Erro ao criar CT-e: {e}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('transportes:cte_tipo', kwargs={'pk': self.object.pk})

class CteUpdateBaseView(CteBaseMixin, UpdateView):
    model = Cte
    template_name = 'transportes/cte_form.html'
    
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
        return reverse('transportes:cte_tipo', kwargs={'pk': self.object.pk})

class CteTipoView(CteUpdateBaseView):
    form_class = CteTipoForm
    active_tab = 'tipo'

    def get_success_url(self):
        return reverse('transportes:cte_rota', kwargs={'pk': self.object.pk})

class CteRotaView(CteUpdateBaseView):
    form_class = CteRotaForm
    active_tab = 'rota'

    def get_success_url(self):
        return reverse('transportes:cte_seguro', kwargs={'pk': self.object.pk})

class CteSeguroView(CteUpdateBaseView):
    form_class = CteSeguroForm
    active_tab = 'seguro'

    def get_success_url(self):
        return reverse('transportes:cte_carga', kwargs={'pk': self.object.pk})

class CteCargaView(CteUpdateBaseView):
    form_class = CteCargaForm
    active_tab = 'carga'

    def get_success_url(self):
        return reverse('transportes:cte_tributacao', kwargs={'pk': self.object.pk})

class CteTributacaoView(CteUpdateBaseView):
    form_class = CteTributacaoForm
    active_tab = 'tributacao'

    def get_success_url(self):
        # Última aba, volta para a mesma ou vai para lista/detalhe
        return reverse('transportes:cte_list')

class CteDeleteView(CteBaseMixin, DeleteView):
    model = Cte
    template_name = 'transportes/cte_confirm_delete.html'
    success_url = reverse_lazy('transportes:cte_list')

    def delete(self, request, *args, **kwargs):
        slug = get_licenca_db_config(self.request)
        self.object = self.get_object()
        if self.object.status not in ['RAS', 'REJ', 'ERR']:
            messages.error(request, "Apenas CT-e em Rascunho, Rejeitado ou Erro podem ser excluídos.")
            return redirect('transportes:cte_list')
        
        try:
            self.object.delete(using=slug)
            messages.success(request, "CT-e excluído com sucesso.")
            return HttpResponseRedirect(self.success_url)
        except Exception as e:
            messages.error(request, f"Erro ao excluir: {e}")
            return redirect('transportes:cte_list')

class CteEmitirView(CteBaseMixin, View):
    def post(self, request, pk):
        slug = get_licenca_db_config(request)
        cte = get_object_or_404(Cte.objects.using(slug), pk=pk)
        
        try:
            # Chama task assíncrona ou service direto (dependendo da configuração)
            # Para feedback imediato na web, as vezes chama direto se for rápido,
            # mas o ideal é task. Vamos chamar task.
            from transportes.tasks.emitir_cte import emitir_cte_task
            
            # Dispara task
            task = emitir_cte_task.delay(cte.id, slug)
            
            messages.info(request, "Emissão iniciada! Acompanhe o status na lista.")
            return redirect('transportes:cte_list')
            
        except Exception as e:
            messages.error(request, f"Erro ao iniciar emissão: {e}")
            return redirect('transportes:cte_list')

class CteConsultarReciboView(CteBaseMixin, View):
    def post(self, request, pk):
        slug = get_licenca_db_config(request)
        cte = get_object_or_404(Cte.objects.using(slug), pk=pk)
        
        if not cte.recibo:
            messages.warning(request, "CT-e não possui recibo para consulta.")
            return redirect('transportes:cte_list')

        try:
            from transportes.tasks.consultar_recibo import consultar_recibo_task
            consultar_recibo_task.delay(cte.id, cte.recibo, slug)
            messages.info(request, "Consulta de recibo iniciada.")
        except Exception as e:
            messages.error(request, f"Erro ao consultar: {e}")
        
        return redirect('transportes:cte_list')
