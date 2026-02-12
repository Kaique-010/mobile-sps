from .base import BaseReportView
from ....service.relatorios_service import RelatorioService
from django.utils.dateparse import parse_date

class RelatorioProdutosPorLoteView(BaseReportView):
    template_name = 'Agricola/Relatorios/produtos_por_lote.html'
    title = "Relatório de Produtos por Lote"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        produto_id = self.request.GET.get('produto_id')
        lote_ident = self.request.GET.get('lote_ident')
        
        context['dados'] = RelatorioService.total_produtos_por_lote(
            self.empresa, 
            self.filial, 
            produto_id=produto_id,
            lote_ident=lote_ident,
            using=self.db_name
        )
        
        context['filtros'] = {
            'produto_id': produto_id,
            'lote_ident': lote_ident
        }
        
        return context

class RelatorioProdutosSemLoteView(BaseReportView):
    template_name = 'Agricola/Relatorios/produtos_sem_lote.html'
    title = "Relatório de Produtos sem Lote"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        produto_id = self.request.GET.get('produto_id')
        
        context['dados'] = RelatorioService.total_produtos_sem_lote(
            self.empresa, 
            self.filial, 
            produto_id=produto_id,
            using=self.db_name
        )
        
        context['filtros'] = {
            'produto_id': produto_id
        }
        
        return context

class RelatorioExtratoMovimentacaoView(BaseReportView):
    template_name = 'Agricola/Relatorios/extrato_movimentacao.html'
    title = "Extrato de Movimentação de Produtos"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtros via GET
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        produto_id = self.request.GET.get('produto_id')
        
        # Converter datas
        dt_ini = parse_date(data_inicio) if data_inicio else None
        dt_fim = parse_date(data_fim) if data_fim else None
        
        context['dados'] = RelatorioService.extrato_movimentacao(
            self.empresa, 
            self.filial, 
            data_inicio=dt_ini,
            data_fim=dt_fim,
            produto_id=produto_id,
            using=self.db_name
        )
        
        # Manter filtros no contexto para o formulário
        context['filtros'] = {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'produto_id': produto_id
        }
        
        return context
