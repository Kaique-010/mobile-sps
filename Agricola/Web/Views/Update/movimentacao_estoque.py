from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from .base import BaseUpdateView
from Agricola.models import MovimentacaoEstoque, Fazenda, ProdutoAgro
from Entidades.models import Entidades
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from Agricola.Web.forms import MovimentacaoEstoqueForm
from Agricola.service.financeiro_service import AgricolaFinanceiroService
from core.utils import get_licenca_db_config
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)

class MovimentacaoEstoqueUpdateView(BaseUpdateView):
    model = MovimentacaoEstoque
    form_class = MovimentacaoEstoqueForm
    template_name = 'Agricola/movimentacao_estoque_form.html'
    def get_success_url(self):
        return reverse('AgricolaWeb:movimentacao_estoque_list', kwargs={'slug': self.kwargs['slug']})
    empresa_field = 'movi_estq_empr'
    filial_field = 'movi_estq_fili'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        # Populate initial values for autocompletes
        if self.object.movi_estq_faze:
            try:
                fazenda = Fazenda.objects.using(db_name).get(id=self.object.movi_estq_faze)
                context['initial_fazenda'] = fazenda.faze_nome
            except (Fazenda.DoesNotExist, ValueError):
                pass
                
        if self.object.movi_estq_prod:
            try:
                produto = ProdutoAgro.objects.using(db_name).get(id=self.object.movi_estq_prod)
                context['initial_produto'] = produto.prod_nome_agro
            except (ProdutoAgro.DoesNotExist, ValueError):
                pass

        if self.object.movi_estq_enti:
            try:
                entidade = Entidades.objects.using(db_name).get(enti_clie=self.object.movi_estq_enti)
                context['initial_entidade'] = entidade.enti_nome
            except (Entidades.DoesNotExist, ValueError):
                pass
                
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Get DB name
        banco = get_licenca_db_config(self.request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')

        # Gerar financeiro se necessário
        try:
            force_financeiro = 'gerar_financeiro' in self.request.POST
            logger.info(f"[MovimentacaoEstoque] Processando form_valid. ID: {self.object.id}, Force: {force_financeiro}, POST keys: {list(self.request.POST.keys())}")
            
            titulo = AgricolaFinanceiroService.gerar_titulo_movimentacao(self.object, using=db_name, force=force_financeiro)
            if titulo:
                logger.info(f"[MovimentacaoEstoque] Título gerado: {titulo.titu_titu}")
                messages.success(self.request, f"Título financeiro gerado com sucesso: {titulo.titu_titu}")
            elif force_financeiro:
                logger.warning(f"[MovimentacaoEstoque] Falha ao gerar título forçado.")
                messages.warning(self.request, "Movimentação salva, mas não foi possível gerar o título financeiro. Verifique se a movimentação possui Entidade e Custo Total.")
        except Exception as e:
            logger.error(f"[MovimentacaoEstoque] Erro: {e}", exc_info=True)
            messages.warning(self.request, f"Movimentação atualizada, mas erro ao processar financeiro: {e}")
            
        return response

    def form_invalid(self, form):
        logger.error(f"[MovimentacaoEstoque] form_invalid: {form.errors}")
        return super().form_invalid(form)

class GerarFinanceiroMovimentacaoView(View):
    def post(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        pk = kwargs.get('pk')
        
        banco = get_licenca_db_config(request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        movimentacao = get_object_or_404(MovimentacaoEstoque.objects.using(db_name), pk=pk)
        
        try:
            titulo = AgricolaFinanceiroService.gerar_titulo_movimentacao(movimentacao, using=db_name, force=True)
            if titulo:
                messages.success(request, f"Título financeiro gerado com sucesso: {titulo.titu_titu}")
            else:
                messages.warning(request, "Não foi possível gerar o título financeiro. Verifique se a movimentação possui Entidade e Custo Total.")
        except Exception as e:
            messages.error(request, f"Erro ao gerar financeiro: {e}")
            
        return redirect('AgricolaWeb:movimentacao_estoque_update', slug=slug, pk=pk)

class MovimentacaoFinanceiroListView(View):
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        
        banco = get_licenca_db_config(request) or 'default'
        db_name = banco if isinstance(banco, str) else banco.get('db_name', 'default')
        
        movimentacao = get_object_or_404(MovimentacaoEstoque.objects.using(db_name), pk=pk)
        
        documento = movimentacao.movi_estq_docu_refe or f"MOV{movimentacao.id}"
        documento = str(documento).strip()
        if not documento:
             documento = f"MOV{movimentacao.id}"
        documento_trunc = documento[:13]
        
        titulos = []
        
        try:
            logger.info(f"[MovimentacaoFinanceiroListView] Buscando títulos para Movimentação {pk}. Doc: {documento_trunc}, Tipo: {movimentacao.movi_estq_tipo}, Entidade: {movimentacao.movi_estq_enti}")
            
            if movimentacao.movi_estq_tipo == 'entrada':
                qs = Titulospagar.objects.using(db_name).filter(
                    titu_empr=movimentacao.movi_estq_empr,
                    titu_fili=movimentacao.movi_estq_fili,
                    titu_forn=movimentacao.movi_estq_enti,
                    titu_titu=documento_trunc,
                    titu_seri="MOV"
                ).order_by('titu_parc')
                logger.info(f"[MovimentacaoFinanceiroListView] Query Entrada: {qs.query}")
            else: # saida
                qs = Titulosreceber.objects.using(db_name).filter(
                    titu_empr=movimentacao.movi_estq_empr,
                    titu_fili=movimentacao.movi_estq_fili,
                    titu_clie=movimentacao.movi_estq_enti,
                    titu_titu=documento_trunc,
                    titu_seri="MOV"
                ).order_by('titu_parc')
                logger.info(f"[MovimentacaoFinanceiroListView] Query Saida: {qs.query}")
                
            logger.info(f"[MovimentacaoFinanceiroListView] Encontrados: {qs.count()} títulos.")
            
            for t in qs:
                titulos.append({
                    'titulo': t.titu_titu,
                    'parcela': t.titu_parc,
                    'vencimento': t.titu_venc.strftime('%d/%m/%Y') if t.titu_venc else '',
                    'valor': float(t.titu_valo) if t.titu_valo else 0.0,
                    'situacao': 'Aberto' if t.titu_situ == 1 else 'Baixado' # Simplificado
                })
                
        except Exception as e:
            logger.error(f"[MovimentacaoFinanceiroListView] Erro: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
            
        return JsonResponse({'results': titulos})
