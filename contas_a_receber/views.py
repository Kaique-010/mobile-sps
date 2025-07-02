from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, models
from django.http import Http404
import logging
from django_filters.rest_framework import DjangoFilterBackend
from core.registry import get_licenca_db_config
from Entidades.models import Entidades 
from core.middleware import get_licenca_slug
from core.decorator import ModuloRequeridoMixin
from .models import Titulosreceber, Baretitulos
from .serializers import TitulosreceberSerializer, BaixaTitulosReceberSerializer, BaretitulosSerializer, ExcluirBaixaSerializer
from decimal import Decimal
from datetime import date

logger = logging.getLogger(__name__)

class TitulosreceberViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modulo_requerido = 'Financeiro'
    serializer_class = TitulosreceberSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'titu_empr': ['exact'],
        'titu_clie': ['exact', 'icontains'],
        'titu_situ': ['exact'],
        'titu_venc': ['gte', 'lte'],
        'titu_aber': ['exact', 'icontains'],
    }
    search_fields = ['titu_titu', 'titu_clie', 'titu_aber']  
    ordering_fields = ['titu_venc', 'titu_valo']
    ordering = ['titu_venc']

    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        queryset = Titulosreceber.objects.using(banco).all()

        cliente_nome = self.request.query_params.get('cliente_nome')
        empresa_id = self.request.query_params.get('titu_empr')

        if cliente_nome:
            ent_qs = Entidades.objects.using(banco).filter(enti_nome__icontains=cliente_nome)
            if empresa_id:
                ent_qs = ent_qs.filter(enti_empr=empresa_id)
            
            clientes_ids = list(ent_qs.values_list('enti_clie', flat=True))
            
            if clientes_ids:
                queryset = queryset.filter(titu_clie__in=clientes_ids)
            else:
                queryset = queryset.none()
        
        return queryset 


    def get_object(self):
        banco = get_licenca_db_config(self.request)
        try:
            # Permitir buscar títulos abertos ('A') ou parcialmente recebidos ('P')
            queryset = Titulosreceber.objects.using(banco).filter(
                titu_empr=self.kwargs["titu_empr"],
                titu_fili=self.kwargs["titu_fili"],
                titu_clie=self.kwargs["titu_clie"],
                titu_titu=self.kwargs["titu_titu"],
                titu_seri=self.kwargs["titu_seri"],
                titu_parc=self.kwargs["titu_parc"],
                titu_emis=self.kwargs["titu_emis"], 
                titu_venc=self.kwargs["titu_venc"], 
                titu_aber__in=['A', 'P']  # Permite títulos abertos ou parcialmente recebidos
            )
            
            if queryset.count() == 0:
                raise Http404("Título não encontrado ou já baixado")
            elif queryset.count() > 1:
                logger.warning(f"Múltiplos títulos encontrados para {self.kwargs}, usando o primeiro")
                return queryset.first()
            else:
                return queryset.get()
        except KeyError as e:
            logger.error(f"Parâmetro obrigatório ausente: {e}")
            raise Http404(f"Parâmetro obrigatório ausente: {e}")
        except Exception as e:
            logger.error(f"Erro ao buscar título: {e}")
            raise Http404("Erro ao buscar título")

    @action(detail=True, methods=['post'])
    def baixar_titulo(self, request, *args, **kwargs):
        """Endpoint para baixar (liquidar) um título a receber"""
        try:
            titulo = self.get_object()
            logger.info(f"Tentando baixar título: {titulo.titu_titu} - Cliente: {titulo.titu_clie}")
        except Http404 as e:
            logger.error(f"Título não encontrado para baixa: {kwargs}")
            return Response(
                {'error': 'Título não encontrado ou já baixado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        banco = get_licenca_db_config(request)
        
        serializer = BaixaTitulosReceberSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Dados inválidos para baixa: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            with transaction.atomic(using=banco):
                # Verificar se o título já está totalmente baixado
                if titulo.titu_aber == 'T':
                    logger.warning(f"Tentativa de baixar título totalmente baixado: {titulo.titu_titu}")
                    return Response(
                        {'error': 'Título já está totalmente baixado'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
            
                valor_titulo = titulo.titu_valo or Decimal('0')
                valor_recebido = data['valor_recebido']
                valor_juros = data.get('valor_juros', Decimal('0'))
                valor_multa = data.get('valor_multa', Decimal('0'))
                valor_desconto = data.get('valor_desconto', Decimal('0'))
                
                valor_total_recebido = valor_recebido + valor_juros + valor_multa - valor_desconto
                
                # Calcular valor já recebido anteriormente (para títulos parciais)
                valor_ja_recebido = Decimal('0')
                if titulo.titu_aber == 'P':
                    baixas_anteriores = Baretitulos.objects.using(banco).filter(
                        bare_empr=titulo.titu_empr,
                        bare_fili=titulo.titu_fili,
                        bare_clie=titulo.titu_clie,
                        bare_titu=titulo.titu_titu,
                        bare_seri=titulo.titu_seri,
                        bare_parc=titulo.titu_parc
                    ).aggregate(total=models.Sum('bare_pago'))['total'] or Decimal('0')
                    valor_ja_recebido = baixas_anteriores
                
                logger.info(f"Valores calculados - Título: {valor_titulo}, Já recebido: {valor_ja_recebido}, Novo recebimento: {valor_total_recebido}")
                
                # Gerar próximo número de sequência
                ultimo_bare = Baretitulos.objects.using(banco).order_by('-bare_sequ').first()
                proximo_sequ = (ultimo_bare.bare_sequ + 1) if ultimo_bare else 1
                
                # Determinar tipo de baixa baseado no valor total (já recebido + novo recebimento)
                valor_total_acumulado = valor_ja_recebido + valor_total_recebido
                if valor_total_acumulado >= valor_titulo:
                    tipo_baixa_final = 'T'  # Total
                else:
                    tipo_baixa_final = 'P'  # Parcial
                
                logger.info(f"Tipo de baixa determinado: {tipo_baixa_final}")
                
                # Criar registro de baixa
                baixa = Baretitulos.objects.using(banco).create(
                    bare_sequ=proximo_sequ,
                    bare_ctrl=titulo.titu_ctrl or 0,
                    bare_empr=titulo.titu_empr,
                    bare_fili=titulo.titu_fili,
                    bare_clie=titulo.titu_clie,
                    bare_titu=titulo.titu_titu, 
                    bare_seri=titulo.titu_seri,
                    bare_parc=titulo.titu_parc,
                    bare_dpag=data['data_recebimento'],
                    bare_apag=valor_titulo,
                    bare_vmul=valor_multa,
                    bare_vjur=valor_juros,
                    bare_vdes=valor_desconto,
                    bare_pago=valor_total_recebido,
                    bare_topa=tipo_baixa_final,
                    bare_banc=data.get('banco'),
                    bare_cheq=data.get('cheque'),
                    bare_hist=data.get('historico', f'Baixa do título {titulo.titu_titu}'),
                    bare_emis=titulo.titu_emis,
                    bare_venc=titulo.titu_venc,
                    bare_cont=titulo.titu_cont,
                    bare_cecu=titulo.titu_cecu,
                    bare_even=titulo.titu_even,
                    bare_port=titulo.titu_port,
                    bare_situ=titulo.titu_situ,
                    bare_usua_baix=request.user.usua_codi if hasattr(request.user, 'usua_codi') else None,
                    bare_data_baix=data['data_recebimento']
                )
                
                Titulosreceber.objects.using(banco).filter(
                    titu_empr=titulo.titu_empr,
                    titu_fili=titulo.titu_fili,
                    titu_clie=titulo.titu_clie,
                    titu_titu=titulo.titu_titu,
                    titu_seri=titulo.titu_seri,
                    titu_parc=titulo.titu_parc,
                    titu_emis=titulo.titu_emis,
                    titu_venc=titulo.titu_venc
                ).update(titu_aber=tipo_baixa_final)
                
                logger.info(f"Baixa realizada com sucesso - ID: {baixa.bare_sequ}")
                
                return Response({
                    'message': 'Título baixado com sucesso',
                    'baixa_id': baixa.bare_sequ,
                    'valor_recebido': valor_total_recebido,
                    'status_titulo': titulo.titu_aber
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Erro ao baixar título {titulo.titu_titu}: {str(e)}")
            return Response(
                {'error': f'Erro ao baixar título: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def get_titulo_for_historico(self):
        """Método para buscar título sem filtrar por status - usado para histórico e exclusão de baixas"""
        banco = get_licenca_db_config(self.request)
        try:
            queryset = Titulosreceber.objects.using(banco).filter(
                titu_empr=self.kwargs["titu_empr"],
                titu_fili=self.kwargs["titu_fili"],
                titu_clie=self.kwargs["titu_clie"],
                titu_titu=self.kwargs["titu_titu"],
                titu_seri=self.kwargs["titu_seri"],
                titu_parc=self.kwargs["titu_parc"],
                titu_emis=self.kwargs["titu_emis"], 
                titu_venc=self.kwargs["titu_venc"]
                
            )
            
            if queryset.count() == 0:
                raise Http404("Título não encontrado")
            elif queryset.count() > 1:
                logger.warning(f"Múltiplos títulos encontrados para {self.kwargs}, usando o primeiro")
                return queryset.first()
            else:
                return queryset.get()
        except KeyError as e:
            logger.error(f"Parâmetro obrigatório ausente: {e}")
            raise Http404(f"Parâmetro obrigatório ausente: {e}")
        except Exception as e:
            logger.error(f"Erro ao buscar título: {e}")
            raise Http404("Erro ao buscar título")

    @action(detail=True, methods=['get'])
    def historico_baixas(self, request, *args, **kwargs):
        """Endpoint para consultar histórico de baixas de um título"""
        titulo = self.get_titulo_for_historico()  # Usar o novo método
        banco = get_licenca_db_config(request)
        
        baixas = Baretitulos.objects.using(banco).filter(
            bare_empr=titulo.titu_empr,
            bare_fili=titulo.titu_fili,
            bare_clie=titulo.titu_clie,
            bare_titu=titulo.titu_titu,  
            bare_seri=titulo.titu_seri,
            bare_parc=titulo.titu_parc
        ).order_by('-bare_dpag')
        
        serializer = BaretitulosSerializer(baixas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def excluir_baixa(self, request, *args, **kwargs):
        """Endpoint para excluir uma baixa específica"""
        titulo = self.get_titulo_for_historico()  # Usar o novo método
        banco = get_licenca_db_config(request)
        
        # Obter ID da baixa dos parâmetros
        baixa_id = request.query_params.get('baixa_id')
        if not baixa_id:
            return Response(
                {'error': 'ID da baixa é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar dados do request body
        serializer = ExcluirBaixaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic(using=banco):
                # Buscar a baixa específica
                baixa = Baretitulos.objects.using(banco).get(
                    bare_sequ=baixa_id,
                    bare_empr=titulo.titu_empr,
                    bare_fili=titulo.titu_fili,
                    bare_clie=titulo.titu_clie,
                    bare_titu=titulo.titu_titu,
                    bare_seri=titulo.titu_seri,
                    bare_parc=titulo.titu_parc
                )
                
                
                # Excluir a baixa
                baixa.delete()
                
                # Recalcular status do título
                baixas_restantes = Baretitulos.objects.using(banco).filter(
                    bare_empr=titulo.titu_empr,
                    bare_fili=titulo.titu_fili,
                    bare_clie=titulo.titu_clie,
                    bare_titu=titulo.titu_titu,
                    bare_seri=titulo.titu_seri,
                    bare_parc=titulo.titu_parc
                )
                
                if baixas_restantes.exists():
                    # Verificar se o valor total das baixas restantes cobre o título
                    valor_total_baixas = baixas_restantes.aggregate(
                        total=models.Sum('bare_pago')
                    )['total'] or Decimal('0')
                    
                    if valor_total_baixas >= titulo.titu_valo:
                        novo_status = 'T'  # Total
                    else:
                        novo_status = 'P'  # Parcial
                else:
                    novo_status = 'A'  # Aberto
                
                # Atualizar status do título
                Titulosreceber.objects.using(banco).filter(
                    titu_empr=titulo.titu_empr,
                    titu_fili=titulo.titu_fili,
                    titu_clie=titulo.titu_clie,
                    titu_titu=titulo.titu_titu,
                    titu_seri=titulo.titu_seri,
                    titu_parc=titulo.titu_parc,
                    titu_emis=titulo.titu_emis,
                    titu_venc=titulo.titu_venc
                ).update(titu_aber=novo_status)
                
                return Response({
                    'message': 'Baixa excluída com sucesso',
                    'baixa_excluida': baixa_id,
                    'novo_status_titulo': novo_status,
                    'motivo': serializer.validated_data.get('motivo_exclusao', '')
                }, status=status.HTTP_200_OK)
                
        except Baretitulos.DoesNotExist:
            return Response(
                {'error': 'Baixa não encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Erro ao excluir baixa: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
