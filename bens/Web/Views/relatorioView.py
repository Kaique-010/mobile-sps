from django.views.generic import TemplateView
from django.utils import timezone
from datetime import datetime
from django.db.models import Q
from core.utils import get_licenca_db_config
from ...models import Bensptr, Grupobens
from ...Web.Services.depreciacao_service import DepreciacaoService

class RelatorioDepreciacaoView(TemplateView):
    template_name = 'Bens/relatorio_depreciacao.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        banco = get_licenca_db_config(self.request) or 'default'
        empresa = self.request.session.get('empresa_id')
        filial = self.request.session.get('filial_id')
        
        # Pega data da requisição GET ou usa hoje
        data_ref_str = self.request.GET.get('data_referencia')
        if data_ref_str:
            try:
                data_referencia = datetime.strptime(data_ref_str, '%Y-%m-%d').date()
            except ValueError:
                data_referencia = timezone.now().date()
        else:
            data_referencia = timezone.now().date()
            
        context['data_referencia'] = data_referencia.strftime('%Y-%m-%d')
        
        # Busca grupos para o dropdown
        grupos_qs = Grupobens.objects.using(banco).all()
        if empresa:
            grupos_qs = grupos_qs.filter(grup_empr=empresa)
        context['grupos'] = grupos_qs.order_by('grup_nome')

        # Filtros
        bens_filtro = self.request.GET.get('bens_filtro', '').strip()
        grupo_filtro = self.request.GET.get('grupo_filtro')

        # Busca bens
        qs = Bensptr.objects.using(banco).all()
        if empresa:
            qs = qs.filter(bens_empr=empresa)
        if filial:
             qs = qs.filter(bens_fili=filial)
             
        if bens_filtro:
            qs = qs.filter(Q(bens_codi__icontains=bens_filtro) | Q(bens_desc__icontains=bens_filtro))
        
        if grupo_filtro:
            qs = qs.filter(bens_grup=grupo_filtro)
            # Para manter selecionado no template, converte para int se possível para comparação correta (se necessário)
            try:
                context['grupo_filtro'] = int(grupo_filtro)
            except (ValueError, TypeError):
                context['grupo_filtro'] = grupo_filtro
        else:
            context['grupo_filtro'] = None
            
        context['bens_filtro'] = bens_filtro

        # Processa cálculos
        resultado = DepreciacaoService.processar_lista_bens(qs, data_referencia)
        
        context.update(resultado)
        
        return context
