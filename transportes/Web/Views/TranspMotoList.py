from django.db.models import CharField, Q
from django.db.models.functions import Cast
from django.views.generic import ListView

from Entidades.models import Entidades
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.services.motorista_documento_status_service import MotoristaDocumentoStatusService


class TranspMotoListView(ListView):
    model = Entidades
    template_name = 'transportes/transp_moto_lista.html'
    context_object_name = 'transp_moto'
    paginate_by = 50

    def _get_banco(self):
        slug = self.kwargs.get('slug')
        return get_db_from_slug(slug) if slug else get_licenca_db_config(self.request)

    def get_queryset(self):
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')
        qs = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien__in=['T', 'M'])

        alerta = (self.request.GET.get('alerta') or '').strip().lower()
        if alerta in {'vencido', 'vencendo'}:
            entidades_ids = MotoristaDocumentoStatusService.entidades_com_alerta(
                banco=banco,
                empresa_id=empresa_id,
                status=alerta,
            )
            if entidades_ids:
                qs = qs.filter(enti_tien='M', enti_clie__in=entidades_ids)
            else:
                return qs.none()

        term = (self.request.GET.get('q') or '').strip()
        if term:
            qs = qs.annotate(enti_clie_str=Cast('enti_clie', output_field=CharField())).filter(
                Q(enti_clie_str__icontains=term) |
                Q(enti_nome__icontains=term) |
                Q(enti_fant__icontains=term)
            )

        tipo = self.request.GET.get('transp_moto_tran')
        if tipo:
            qs = qs.filter(enti_tien=tipo)

        transp_moto_clie = (self.request.GET.get('transp_moto_clie') or '').strip()
        if transp_moto_clie:
            qs = qs.annotate(enti_clie_str=Cast('enti_clie', output_field=CharField())).filter(
                enti_clie_str__icontains=transp_moto_clie
            )

        return qs.order_by('enti_tien', 'enti_clie')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        banco = self._get_banco()
        empresa_id = self.request.session.get('empresa_id')

        base_qs = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien__in=['T', 'M'])
        context['titulo'] = 'Transportadoras e Motoristas'
        context['total_transportadoras_motoristas'] = base_qs.count()
        context['total_transportadoras'] = base_qs.filter(enti_tien='T').count()
        context['total_motoristas'] = base_qs.filter(enti_tien='M').count()

        context['painel_alertas_documentos'] = MotoristaDocumentoStatusService.montar_painel_alertas(
            banco=banco,
            empresa_id=empresa_id,
        )
        alerta = (self.request.GET.get('alerta') or '').strip().lower()
        context['alerta_tipo'] = alerta if alerta in {'vencido', 'vencendo'} else ''
        if context['alerta_tipo']:
            itens = MotoristaDocumentoStatusService.listar_itens_alerta(
                banco=banco,
                empresa_id=empresa_id,
                status=context['alerta_tipo'],
            )
            ids = {i.entidade_id for i in itens}
            entidades = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_clie__in=ids).only(
                'enti_clie',
                'enti_nome',
                'enti_fant',
                'enti_tien',
            )
            entidades_por_id = {e.enti_clie: e for e in entidades}
            context['alertas_itens'] = [
                {
                    'entidade_id': item.entidade_id,
                    'entidade_nome': getattr(entidades_por_id.get(item.entidade_id), 'enti_nome', '') or '',
                    'entidade_fant': getattr(entidades_por_id.get(item.entidade_id), 'enti_fant', '') or '',
                    'origem': item.origem,
                    'descricao': item.descricao,
                    'data_validade': item.data_validade,
                    'dias_restantes': item.dias_restantes,
                    'status': item.status,
                }
                for item in itens
            ]
        context['slug'] = self.kwargs.get('slug')
        return context
        return context
