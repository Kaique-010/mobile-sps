from django.views.generic import ListView
from django.db.models import CharField, Q
from django.db.models.functions import Cast
from core.utils import get_licenca_db_config
from Entidades.models import Entidades

class TranspMotoListView(ListView):
    model = Entidades
    template_name = 'transportes/transp_moto_lista.html'
    context_object_name = 'transp_moto'
    paginate_by = 50

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get('empresa_id')
        qs = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien__in=['T', 'M'])
        # Filtro genérico (q)
        term = (self.request.GET.get('q') or '').strip()
        if term:
            qs = qs.annotate(enti_clie_str=Cast('enti_clie', output_field=CharField()))
            qs = qs.filter(
                Q(enti_clie_str__icontains=term) |
                Q(enti_nome__icontains=term) |
                Q(enti_fant__icontains=term)
            )

        # Filtros específicos
        transp_moto_tran = self.request.GET.get('transp_moto_tran')
        if transp_moto_tran:
            qs = qs.filter(enti_tien=transp_moto_tran)

        transp_moto_clie = (self.request.GET.get('transp_moto_clie') or '').strip()
        if transp_moto_clie:
            qs = qs.annotate(enti_clie_str=Cast('enti_clie', output_field=CharField()))
            qs = qs.filter(enti_clie_str__icontains=transp_moto_clie)
        
        return qs.order_by('enti_tien', 'enti_clie', 'enti_nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = get_licenca_db_config(self.request)
        empresa_id = self.request.session.get('empresa_id')
        
        context['titulo'] = 'Transportadoras e Motoristas'
        # Contagem total para exibir no card
        context['total_transportadoras_motoristas'] = self.get_queryset().count()
        
        # Contagem de Transportadoras
        context['total_transportadoras'] = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien='T').count()
        
        # Contagem de Motoristas    
        context['total_motoristas'] = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien='M').count()
        
        # Lista de transportadoras para o filtro
        context['transportadoras'] = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien='T').order_by('enti_clie')
        
        # Lista de motoristas para o filtro
        context['motoristas'] = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien='M').order_by('enti_clie')

        return context
