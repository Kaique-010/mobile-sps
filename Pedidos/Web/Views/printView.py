from django.views.generic import DetailView
from django.http import Http404
import logging
import base64
from core.utils import get_licenca_db_config
from ...models import PedidoVenda
from Licencas.models import Empresas, Filiais
from Entidades.models import Entidades
from Produtos.models import Produtos
from ...models import Itenspedidovenda

logger = logging.getLogger(__name__)


class PedidoPrintView(DetailView):
    model = PedidoVenda
    template_name = 'Pedidos/pedido_impressao.html'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.session.get('empresa_id', 1)
        filial_id = self.request.session.get('filial_id', 1)
        return PedidoVenda.objects.using(banco).filter(
            pedi_empr=int(empresa_id),
            pedi_fili=int(filial_id)
        )

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        try:
            pk = int(self.kwargs.get(self.pk_url_kwarg))
        except Exception:
            raise Http404("Pedido inválido")
        obj = queryset.filter(pedi_nume=pk).first()
        if not obj:
            raise Http404("Pedido não encontrado")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['slug'] = self.kwargs.get('slug')

        try:
            banco = get_licenca_db_config(self.request) or 'default'
            pedido = context.get('object')

            if pedido:
                # Carregar Empresa e Filial
                context['empresa'] = Empresas.objects.using(banco).filter(
                    empr_codi=pedido.pedi_empr
                ).first()
                
                context['filial'] = Filiais.objects.using(banco).filter(
                    empr_empr=pedido.pedi_empr,
                    empr_codi=pedido.pedi_fili
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
                context['cliente'] = Entidades.objects.using(banco).filter(
                    enti_empr=pedido.pedi_empr,
                    enti_clie=pedido.pedi_forn
                ).first()

                # Carregar Vendedor
                context['vendedor'] = Entidades.objects.using(banco).filter(
                    enti_empr=pedido.pedi_empr,
                    enti_clie=pedido.pedi_vend
                ).first()

                # Carregar Itens
                try:
                    itens_qs = Itenspedidovenda.objects.using(banco).filter(
                        iped_empr=pedido.pedi_empr,
                        iped_fili=pedido.pedi_fili,
                        iped_pedi=str(pedido.pedi_nume)
                    ).order_by('iped_item')
                except Exception:
                    itens_qs = []

                # Otimização de produtos
                codigos = [i.iped_prod for i in itens_qs]
                produtos = Produtos.objects.using(banco).filter(prod_codi__in=codigos, prod_empr=str(pedido.pedi_empr))
                prod_map = {p.prod_codi: {'nome': p.prod_nome, 'unidade': p.prod_unme_id, 'has_foto': bool(p.prod_foto)} for p in produtos}

                itens_detalhados = []
                for i in itens_qs:
                    meta = prod_map.get(i.iped_prod, {})
                    itens_detalhados.append({
                        'prod_codigo': i.iped_prod,
                        'prod_nome': meta.get('nome') or i.iped_prod,
                        'prod_unidade': meta.get('unidade') or i.iped_unme,
                        'has_foto': bool(meta.get('has_foto')),
                        'iped_quan': i.iped_quan,
                        'iped_unit': i.iped_unit,
                        'iped_tota': i.iped_tota,
                        'iped_desc': i.iped_desc,
                        'iped_item': getattr(i, 'iped_item', None),
                    })
                context['itens_detalhados'] = itens_detalhados
                
        except Exception as e:
            logger.error(f"Erro ao carregar dados da impressão: {e}")
            context['error_msg'] = "Erro ao carregar dados completos."

        return context
