from django.views.generic import DetailView
from django.http import Http404
import logging
import base64
from core.utils import get_licenca_db_config
from ...models import Os, PecasOs, ServicosOs
from Licencas.models import Empresas, Filiais
from Entidades.models import Entidades
from Produtos.models import Produtos

logger = logging.getLogger(__name__)


class OsPrintView(DetailView):
    model = Os
    template_name = 'Os/os_impressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        return Os.objects.using(banco).filter(
            os_empr=int(empresa_id),
            os_fili=int(filial_id)
        )

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        try:
            pk = int(self.kwargs.get(self.pk_url_kwarg))
        except Exception:
            raise Http404("Ordem de Serviço inválida")
        obj = queryset.filter(os_os=pk).first()
        if not obj:
            raise Http404("Ordem de Serviço não encontrada")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')

        try:
            banco = get_licenca_db_config(self.request) or 'default'
            os_obj = context.get('object')

            if os_obj:
                # Carregar Empresa e Filial
                context['empresa'] = Empresas.objects.using(banco).filter(
                    empr_codi=os_obj.os_empr
                ).first()
                
                context['filial'] = Filiais.objects.using(banco).filter(
                    empr_empr=os_obj.os_empr,
                    empr_codi=os_obj.os_fili
                ).first()

                # Processar Logo
                if context['filial'] and context['filial'].empr_logo:
                    try:
                        # Se for bytes (BinaryField), converte para base64
                        logo_data = context['filial'].empr_logo
                        if isinstance(logo_data, memoryview):
                            logo_data = logo_data.tobytes()
                        if isinstance(logo_data, bytes):
                            context['logo_b64'] = base64.b64encode(logo_data).decode('utf-8')
                    except Exception as e:
                        logger.error(f"Erro ao processar logo: {e}")

                # Carregar Cliente
                if os_obj.os_clie:
                    context['cliente'] = Entidades.objects.using(banco).filter(
                        enti_empr=os_obj.os_empr,
                        enti_clie=os_obj.os_clie
                    ).first()

                # Carregar Vendedor
                if os_obj.os_prof_aber:
                    context['vendedor'] = Entidades.objects.using(banco).filter(
                        enti_empr=os_obj.os_empr,
                        enti_clie=os_obj.os_prof_aber
                    ).first()

                # Carregar Itens (Peças e Serviços)
                pecas_qs = []
                servicos_qs = []
                
                try:
                    pecas_qs = PecasOs.objects.using(banco).filter(
                        peca_empr=os_obj.os_empr,
                        peca_fili=os_obj.os_fili,
                        peca_os=os_obj.os_os
                    ).order_by('peca_item')
                except Exception:
                    pass

                try:
                    servicos_qs = ServicosOs.objects.using(banco).filter(
                        serv_empr=os_obj.os_empr,
                        serv_fili=os_obj.os_fili,
                        serv_os=os_obj.os_os
                    ).order_by('serv_item')
                except Exception:
                    pass

                # Otimização de produtos (Peças)
                pecas_codigos = [p.peca_prod for p in pecas_qs]
                produtos_pecas = Produtos.objects.using(banco).filter(prod_codi__in=pecas_codigos, prod_empr=str(os_obj.os_empr))
                prod_map = {p.prod_codi: {'nome': p.prod_nome, 'unidade': p.prod_unme_id, 'has_foto': bool(p.prod_foto)} for p in produtos_pecas}

                # Otimização de serviços (Produtos tipo serviço)
                serv_codigos = [s.serv_prod for s in servicos_qs]
                produtos_serv = Produtos.objects.using(banco).filter(prod_codi__in=serv_codigos, prod_empr=str(os_obj.os_empr))
                serv_map = {p.prod_codi: {'nome': p.prod_nome, 'unidade': p.prod_unme_id} for p in produtos_serv}

                # Processar Peças
                pecas_detalhadas = []
                for i in pecas_qs:
                    meta = prod_map.get(i.peca_prod, {})
                    pecas_detalhadas.append({
                        'codigo': i.peca_prod,
                        'descricao': meta.get('nome') or i.peca_prod,
                        'unidade': meta.get('unidade') or 'UN',
                        'qtd': i.peca_quan,
                        'unit': i.peca_unit,
                        'total': i.peca_tota,
                        'tipo': 'Peça'
                    })

                # Processar Serviços
                servicos_detalhados = []
                for i in servicos_qs:
                    meta = serv_map.get(i.serv_prod, {})
                    servicos_detalhados.append({
                        'codigo': i.serv_prod,
                        'descricao': meta.get('nome') or i.serv_prod,
                        'unidade': meta.get('unidade') or 'SV',
                        'qtd': i.serv_quan,
                        'unit': i.serv_unit,
                        'total': i.serv_tota,
                        'tipo': 'Serviço'
                    })
                
                context['pecas_detalhadas'] = pecas_detalhadas
                context['servicos_detalhados'] = servicos_detalhados
                
                # Calcular totais separados para exibição se necessário
                context['total_pecas'] = sum(p['total'] for p in pecas_detalhadas if p['total'])
                context['total_servicos'] = sum(s['total'] for s in servicos_detalhados if s['total'])

        except Exception as e:
            logger.error(f"Erro ao carregar dados da impressão de OS: {e}")
            context['error_msg'] = "Erro ao carregar dados completos da OS."
            
        return context