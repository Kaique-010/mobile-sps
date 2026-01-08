from rest_framework.viewsets import ModelViewSet
from rest_framework import status, filters
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Max
from rest_framework.decorators import action
from core.registry import get_licenca_db_config
from core.impressoes.pdf import PDFBuilder
from io import BytesIO
from .serializers import OsexternaSerializer, ServicososexternaSerializer
from ..services.entidade_dados import DadosEntidadesService
from ..models import Osexterna, Servicososexterna
import base64
import logging

logger = logging.getLogger(__name__)

class BaseMultiDBModelViewSet(ModelViewSet):
    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            raise NotFound("Banco de dados não encontrado.")
        return banco

    def get_queryset(self):
        return super().get_queryset().using(self.get_banco())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

class OsexternaViewSet(BaseMultiDBModelViewSet):
    queryset = Osexterna.objects.all()
    serializer_class = OsexternaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['osex_empr', 'osex_fili', 'osex_codi']
    search_fields = ['osex_cida']
    
    def get_queryset(self):
        banco = self.get_banco()
        qs = Osexterna.objects.using(banco).all()

        return qs.order_by('-osex_data_aber')
    
    def get_object(self):
        banco = self.get_banco()
        try:
            logger.info(f"Buscando OS com pk={self.kwargs['pk']} no banco {banco}")
            return Osexterna.objects.using(banco).get(pk=self.kwargs['pk'])
        except Osexterna.DoesNotExist:
            raise NotFound("Ordem de Serviço não encontrada.")

    def _next_global_codigo(self):
        banco = self.get_banco()
        ultimo = Osexterna.objects.using(banco).aggregate(Max('osex_codi'))['osex_codi__max']
        return (ultimo or 0) + 1

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        if not data.get('osex_codi'):
            data['osex_codi'] = self._next_global_codigo()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            instance = serializer.save()
            instance = DadosEntidadesService.preencher_dados_do_cliente(instance, request)
            instance.save(using=banco)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['patch'], url_path='patch')
    def patch_ordem(self, request, slug=None):
        banco = self.get_banco()
        osex_pk = request.data.get('osex_codi') or request.data.get('pk')
        if not osex_pk:
            return Response({'detail': 'osex_codi obrigatório'}, status=400)
        try:
            instance = Osexterna.objects.using(banco).get(pk=osex_pk)
        except Osexterna.DoesNotExist:
            raise NotFound('Ordem Externa não encontrada.')
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            self.perform_update(serializer)
        return Response(serializer.data)


    @action(detail=True, methods=['get'])
    def imprimir(self, request, pk=None, slug=None):
        banco = self.get_banco()
        osex = self.get_object()

        try:
            from Entidades.models import Entidades
            from Licencas.models import Filiais
            cliente = Entidades.objects.using(banco).filter(enti_clie=osex.osex_clie).first()
            filial = Filiais.objects.using(banco).filter(empr_empr=osex.osex_empr, empr_codi=osex.osex_fili).first()
        except Exception:
            cliente = None
            filial = None

        servicos = Servicososexterna.objects.using(banco).filter(
            serv_empr=osex.osex_empr,
            serv_fili=osex.osex_fili,
            serv_os=osex.osex_codi,
        )

        buffer = BytesIO()
        pdf = PDFBuilder(buffer)
        pdf.add_title(f"O.S. Externa Nº {osex.osex_codi}")

        filial_nome = getattr(filial, "empr_fant", None) or getattr(filial, "empr_nome", "")
        pdf.add_label_value("Empresa", filial_nome)
        pdf.add_label_value("Data Abertura", getattr(osex, "osex_data_aber", "") or "")
        pdf.add_label_value("Cliente", getattr(cliente, "enti_nome", "") or str(osex.osex_clie))
        pdf.add_label_value("Responsável", str(osex.osex_resp or ""))
        pdf.add_label_value("Cidade", getattr(osex, "osex_cida", "") or "")
        pdf.add_label_value("Total", f"R$ {str(osex.osex_valo_tota or 0)}")

        dados_servicos = [["Descrição", "Qtd", "Unit", "Total"]]
        for s in servicos:
            dados_servicos.append([
                getattr(s, "serv_desc", "") or getattr(s, "serv_comp", "") or "",
                str(getattr(s, "serv_quan", "") or ""),
                str(getattr(s, "serv_valo_unit", "") or ""),
                str(getattr(s, "serv_valo_tota", "") or ""),
            ])
        pdf.add_table(dados_servicos, col_widths=[420, 80, 100, 100])

        try:
            clie_sig = getattr(osex, 'osex_assi_clie', None)
            oper_sig = getattr(osex, 'osex_assi_oper', None)

            def _to_base64(val):
                if not val:
                    return None
                if isinstance(val, memoryview):
                    val = val.tobytes()
                if isinstance(val, bytes):
                    # bytes podem conter data URL como texto
                    try:
                        s = val.decode('utf-8')
                        if s.startswith('data:image/'):
                            try:
                                return s.split('base64,', 1)[1]
                            except Exception:
                                return s
                    except Exception:
                        pass
                    return base64.b64encode(val).decode('utf-8')
                if isinstance(val, str):
                    if val.startswith('data:image/'):
                        try:
                            return val.split('base64,', 1)[1]
                        except Exception:
                            return val
                    return val
                try:
                    return base64.b64encode(str(val).encode('utf-8')).decode('utf-8')
                except Exception:
                    return None

            clie_b64 = _to_base64(clie_sig)
            oper_b64 = _to_base64(oper_sig)

            if clie_b64:
                pdf.add_signature("Assinatura do Cliente", clie_b64)
            if oper_b64:
                pdf.add_signature("Assinatura do Operador", oper_b64)
        except Exception:
            pass

        pdf.build()
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="osex_{osex.osex_codi}.pdf"'
        return response

    @action(detail=False, methods=['get'], url_path='preco')
    def preco(self, request):
        banco = self.get_banco()
        empresa_id = request.session.get('empresa_id', 1)
        filial_id = request.session.get('filial_id', 1)
        prod_codi = (request.GET.get('prod_codi') or '').strip()
        tipo_financeiro = (request.GET.get('tipo') or request.GET.get('pedi_fina') or '1')
        try:
            from Produtos.models import Tabelaprecos
            qs = Tabelaprecos.objects.using(banco).filter(
                tabe_empr=str(empresa_id),
                tabe_fili=str(filial_id),
                tabe_prod=str(prod_codi)
            )
            tp = qs.first()
            if not tp:
                return Response({'unit_price': None, 'found': False})
            if str(tipo_financeiro) == '1':
                price = tp.tabe_avis or tp.tabe_prco or tp.tabe_praz
            else:
                price = tp.tabe_praz or tp.tabe_prco or tp.tabe_avis
            try:
                unit_price = float(price or 0)
            except Exception:
                unit_price = 0.0
            return Response({'unit_price': unit_price, 'found': True})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class ServicososexternaViewSet(BaseMultiDBModelViewSet):
    queryset = Servicososexterna.objects.all()
    serializer_class = ServicososexternaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['serv_empr', 'serv_fili', 'serv_os', 'serv_sequ']
    search_fields = ['serv_desc']

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"ServicososexternaViewSet.dispatch: method={request.method}, path={request.path}, GET={request.GET}")
        return super().dispatch(request, *args, **kwargs)

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        logger.info(f"ServicososexternaViewSet.filter_queryset: original_count={queryset.count()}, filtered_count={qs.count()}")
        return qs

    def get_queryset(self):
        banco = self.get_banco()
        qs = Servicososexterna.objects.using(banco).all()
        logger.info(f"ServicososexternaViewSet.get_queryset: banco={banco}, count={qs.count()}")
        return qs

    def _next_global_sequ(self):
        banco = self.get_banco()
        ultimo = Servicososexterna.objects.using(banco).aggregate(Max('serv_sequ'))['serv_sequ__max']
        return (ultimo or 0) + 1
    
    def get_object(self):
        banco = self.get_banco()
        # Se for update-lista ou create, não tem pk na URL geralmente, mas get_object é pra detail
        # Tenta pegar pk da URL
        pk = self.kwargs.get('pk')
        if pk:
            logger.info(f"Buscando Servico com serv_sequ={pk} no banco {banco}")
            try:
                obj = Servicososexterna.objects.using(banco).get(serv_sequ=pk)
                self.check_object_permissions(self.request, obj)
                return obj
            except Servicososexterna.DoesNotExist:
                raise NotFound("Serviço não encontrado.")
        
        # Fallback antigo (mas perigoso pois pega o primeiro)
        queryset = self.filter_queryset(self.get_queryset())
        obj = queryset.first()
        if not obj:
            raise NotFound("Objeto não encontrado")
        self.check_object_permissions(self.request, obj)
        return obj

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()
        if not data.get('serv_sequ'):
            data['serv_sequ'] = self._next_global_sequ()
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = self.get_banco()
        itens = request.data if isinstance(request.data, list) else request.data.get('itens') or []
        if not isinstance(itens, list):
            return Response({'detail': 'Lista de itens inválida'}, status=400)
        atualizados = []
        meta_os = None
        with transaction.atomic(using=banco):
            for item in itens:
                data = item.copy()
                if not data.get('serv_sequ'):
                    data['serv_sequ'] = self._next_global_sequ()
                inst = None
                if data.get('serv_sequ'):
                    try:
                        inst = Servicososexterna.objects.using(banco).get(pk=data['serv_sequ'])
                    except Servicososexterna.DoesNotExist:
                        inst = None
                ser = self.get_serializer(inst, data=data, partial=bool(inst))
                ser.is_valid(raise_exception=True)
                ser.save()
                atualizados.append(ser.data)
                if not meta_os:
                    meta_os = {
                        'serv_empr': data.get('serv_empr'),
                        'serv_fili': data.get('serv_fili'),
                        'serv_os': data.get('serv_os'),
                    }
        # Recalcular total da OS se contexto disponível
        try:
            if meta_os and all(meta_os.values()):
                from django.db.models import Sum
                total = Servicososexterna.objects.using(banco).filter(
                    serv_empr=meta_os['serv_empr'],
                    serv_fili=meta_os['serv_fili'],
                    serv_os=meta_os['serv_os'],
                ).aggregate(total=Sum('serv_valo_tota'))['total'] or 0
                os_inst = Osexterna.objects.using(banco).get(
                    osex_empr=meta_os['serv_empr'],
                    osex_fili=meta_os['serv_fili'],
                    osex_codi=meta_os['serv_os'],
                )
                os_inst.osex_valo_tota = total
                os_inst.save(using=banco)
        except Exception:
            pass
        return Response({'itens': atualizados})

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context
    
@staticmethod
def _apply_entidade_service_after_update(viewset, serializer):
    banco = viewset.get_banco()
    instance = serializer.save()
    instance = DadosEntidadesService.preencher_dados_do_cliente(instance, viewset.request)
    instance.save(using=banco)

OsexternaViewSet.perform_update = lambda self, serializer: _apply_entidade_service_after_update(self, serializer)
