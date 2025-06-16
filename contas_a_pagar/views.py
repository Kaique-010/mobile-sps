from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.http import Http404  # ✅ Adicionar
from django_filters.rest_framework import DjangoFilterBackend
from .models import Titulospagar, Bapatitulos
from Entidades.models import Entidades 
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from .serializers import TitulospagarSerializer, BaixaTitulosPagarSerializer, BapatitulosSerializer
from decimal import Decimal
from datetime import date

class TitulospagarViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'Financeiro'
    serializer_class = TitulospagarSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'titu_empr': ['exact'],
        'titu_forn': ['exact'],
        'titu_titu': ['exact'],
        'titu_venc': ['gte', 'lte'],
        'titu_aber': ['exact'],
    }
    search_fields = ['titu_titu', 'titu_aber']
    ordering_fields = ['titu_emis','titu_venc', 'titu_valo']
    ordering = ['-titu_emis']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        queryset = Titulospagar.objects.using(banco).all()

        fornecedor_nome = self.request.query_params.get('fornecedor_nome')
        empresa_id = self.request.query_params.get('titu_empr')

        if fornecedor_nome:
            ent_qs = Entidades.objects.using(banco).filter(enti_nome__icontains=fornecedor_nome)
            if empresa_id:
                ent_qs = ent_qs.filter(enti_empr=empresa_id)
            
            fornecedor_ids = list(ent_qs.values_list('enti_clie', flat=True))
            
            if fornecedor_ids:
                queryset = queryset.filter(titu_forn__in=fornecedor_ids)
            else:
                queryset = queryset.none()
        
        return queryset 


            

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        try:
            queryset = Titulospagar.objects.using(banco).filter(
                titu_empr=self.kwargs["titu_empr"],
                titu_fili=self.kwargs["titu_fili"],
                titu_forn=self.kwargs["titu_forn"],
                titu_titu=self.kwargs["titu_titu"],
                titu_seri=self.kwargs["titu_seri"],
                titu_parc=self.kwargs["titu_parc"],
                titu_emis=self.kwargs["titu_emis"],
                titu_venc=self.kwargs["titu_venc"],
                titu_aber='A'
            )
            
            if queryset.count() == 0:
                raise Http404("Título não encontrado ou já baixado")
            elif queryset.count() > 1:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Múltiplos títulos encontrados para os critérios: {self.kwargs}")
                return queryset.first()
            else:
                return queryset.get()
        except KeyError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Parâmetro obrigatório ausente: {e}")
            raise Http404(f"Parâmetro obrigatório ausente: {e}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao buscar título: {e}")
            raise Http404("Erro ao buscar título")

    @action(detail=True, methods=['post'])
    def baixar_titulo(self, request, *args, **kwargs):
        """Endpoint para baixar (liquidar) um título a pagar"""
        titulo = self.get_object()
        banco = get_licenca_db_config(request)
        
        serializer = BaixaTitulosPagarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            with transaction.atomic(using=banco):
            
                if titulo.titu_aber == 'T' or titulo.titu_aber == 'P':
                    return Response(
                        {'error': 'Título já está baixado'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Calcular valores
                valor_titulo = titulo.titu_valo or Decimal('0')
                valor_pago = data['valor_pago']
                valor_juros = data.get('valor_juros', Decimal('0'))
                valor_multa = data.get('valor_multa', Decimal('0'))
                valor_desconto = data.get('valor_desconto', Decimal('0'))
                
                valor_total_pago = valor_pago + valor_juros + valor_multa - valor_desconto
                
                # Gerar próximo número de sequência
                ultimo_bapa = Bapatitulos.objects.using(banco).order_by('-bapa_sequ').first()
                proximo_sequencial = (ultimo_bapa.bapa_sequ + 1) if ultimo_bapa else 1
                
                # Determinar tipo de baixa baseado no valor pago
                if valor_total_pago >= valor_titulo:
                    tipo_baixa_final = 'T'  # Total
                else:
                    tipo_baixa_final = 'P'  # Parcial
                
                baixa = Bapatitulos.objects.using(banco).create(
                    bapa_sequ=proximo_sequencial,
                    bapa_ctrl=titulo.titu_ctrl or 0,
                    bapa_empr=titulo.titu_empr,
                    bapa_fili=titulo.titu_fili,
                    bapa_forn=titulo.titu_forn,
                    bapa_titu=titulo.titu_titu,
                    bapa_seri=titulo.titu_seri,
                    bapa_parc=titulo.titu_parc,
                    bapa_dpag=data['data_pagamento'],
                    bapa_apag=valor_titulo,
                    bapa_vmul=valor_multa,
                    bapa_vjur=valor_juros,
                    bapa_vdes=valor_desconto,
                    bapa_pago=valor_total_pago,
                    bapa_topa=tipo_baixa_final, 
                    bapa_banc=data.get('banco'),
                    bapa_cheq=data.get('cheque'),
                    bapa_hist=data.get('historico', f'Baixa do título {titulo.titu_titu}'),
                    bapa_emis=titulo.titu_emis,
                    bapa_venc=titulo.titu_venc,
                    bapa_cont=titulo.titu_cont,
                    bapa_cecu=titulo.titu_cecu,
                    bapa_even=titulo.titu_even,
                    bapa_port=titulo.titu_port,
                    bapa_situ=titulo.titu_situ
                )
                
                Titulospagar.objects.using(banco).filter(
                    titu_empr=titulo.titu_empr,
                    titu_fili=titulo.titu_fili,
                    titu_forn=titulo.titu_forn,
                    titu_titu=titulo.titu_titu,
                    titu_seri=titulo.titu_seri,
                    titu_parc=titulo.titu_parc,
                    titu_emis=titulo.titu_emis,
                    titu_venc=titulo.titu_venc
                ).update(titu_aber=tipo_baixa_final)
                
                return Response({
                    'message': 'Título baixado com sucesso',
                    'baixa_id': baixa.bapa_sequ,
                    'valor_pago': valor_total_pago,
                    'status_titulo': titulo.titu_aber
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {'error': f'Erro ao baixar título: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def historico_baixas(self, request, *args, **kwargs):
        """Endpoint para consultar histórico de baixas de um título"""
        titulo = self.get_object()
        banco = get_licenca_db_config(request)
        
        baixas = Bapatitulos.objects.using(banco).filter(
            bapa_empr=titulo.titu_empr,
            bapa_fili=titulo.titu_fili,
            bapa_forn=titulo.titu_forn,
            bapa_titu=titulo.titu_titu,
            bapa_seri=titulo.titu_seri,
            bapa_parc=titulo.titu_parc
        ).order_by('-bapa_dpag')
        
        serializer = BapatitulosSerializer(baixas, many=True)
        return Response(serializer.data)
