from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, models
from django.http import Http404  # ✅ Adicionar
from django_filters.rest_framework import DjangoFilterBackend
from .models import Titulospagar, Bapatitulos
from Entidades.models import Entidades 
from core.registry import get_licenca_db_config
from core.middleware import get_licenca_slug
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from .serializers import TitulospagarSerializer, BaixaTitulosPagarSerializer, BapatitulosSerializer, ExcluirBaixaSerializer
from decimal import Decimal
from datetime import date
from Lancamentos_Bancarios.utils import criar_lancamento_bancario_baixa

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
                titu_aber__in=['A', 'P']  
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

    def get_titulo_for_historico(self):
     
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
                titu_venc=self.kwargs["titu_venc"]
              
            )
            
            if queryset.count() == 0:
                raise Http404("Título não encontrado")
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

    @action(detail=True, methods=['get'])
    def historico_baixas(self, request, *args, **kwargs):
        titulo = self.get_titulo_for_historico()  # Usar o método específico
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

    @action(detail=True, methods=['delete'])
    def excluir_baixa(self, request, *args, **kwargs):
        """Endpoint para excluir uma baixa específica de um título"""
        titulo = self.get_titulo_for_historico()  # Usar método corrigido
        banco = get_licenca_db_config(request)
        
        # Obter baixa_id dos query parameters ou da URL (alias REST)
        baixa_id = request.query_params.get('baixa_id') or kwargs.get('baixa_id')
        
        if not baixa_id:
            return Response(
                {'error': 'ID da baixa é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar dados do request body com o serializer
        serializer = ExcluirBaixaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic(using=banco):
                # Buscar a baixa específica
                baixa = Bapatitulos.objects.using(banco).get(
                    bapa_sequ=baixa_id,
                    bapa_empr=titulo.titu_empr,
                    bapa_fili=titulo.titu_fili,
                    bapa_forn=titulo.titu_forn,
                    bapa_titu=titulo.titu_titu,
                    bapa_seri=titulo.titu_seri,
                    bapa_parc=titulo.titu_parc
                )
                
               
                # Excluir a baixa
                baixa.delete()
                
                # Recalcular status do título
                baixas_restantes = Bapatitulos.objects.using(banco).filter(
                    bapa_empr=titulo.titu_empr,
                    bapa_fili=titulo.titu_fili,
                    bapa_forn=titulo.titu_forn,
                    bapa_titu=titulo.titu_titu,
                    bapa_seri=titulo.titu_seri,
                    bapa_parc=titulo.titu_parc
                )
                
                if baixas_restantes.exists():
                    # Verificar se o valor total das baixas restantes cobre o título
                    valor_total_baixas = baixas_restantes.aggregate(
                        total_valo_pago=models.Sum('bapa_valo_pago'),
                        total_sub_tota=models.Sum('bapa_sub_tota')
                    )
                    # Usar bapa_valo_pago como prioridade, se não existir usar bapa_sub_tota
                    total_pago = (valor_total_baixas['total_valo_pago'] or 
                                valor_total_baixas['total_sub_tota'] or 
                                Decimal('0'))
                    
                    if total_pago >= titulo.titu_valo:
                        novo_status = 'T'  # Total
                    else:
                        novo_status = 'P'  # Parcial
                else:
                    novo_status = 'A'  # Aberto
                
                # Atualizar status do título
                Titulospagar.objects.using(banco).filter(
                    titu_empr=titulo.titu_empr,
                    titu_fili=titulo.titu_fili,
                    titu_forn=titulo.titu_forn,
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
                
        except Bapatitulos.DoesNotExist:
            return Response(
                {'error': 'Baixa não encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Erro ao excluir baixa: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def baixar_titulo(self, request, *args, **kwargs):
        """Endpoint para baixar (liquidar) um título a pagar"""
        try:
            titulo = self.get_object()
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Tentando baixar título: {titulo.titu_titu} - Fornecedor: {titulo.titu_forn}")
        except Http404 as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Título não encontrado para baixa: {kwargs}")
            return Response(
                {'error': 'Título não encontrado ou já baixado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        banco = get_licenca_db_config(request)
        
        serializer = BaixaTitulosPagarSerializer(data=request.data)
        if not serializer.is_valid():
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Dados inválidos para baixa: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            with transaction.atomic(using=banco):
                # Verificar se o título já está totalmente baixado
                if titulo.titu_aber == 'T':
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Tentativa de baixar título totalmente baixado: {titulo.titu_titu}")
                    return Response(
                        {'error': 'Título já está totalmente baixado'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                valor_titulo = titulo.titu_valo or Decimal('0')
                valor_pago = data['valor_pago']
                valor_juros = data.get('valor_juros', Decimal('0'))
                valor_multa = data.get('valor_multa', Decimal('0'))
                valor_desconto = data.get('valor_desconto', Decimal('0'))
                
                valor_total_pago = valor_pago + valor_juros + valor_multa - valor_desconto
                
                # Calcular valor já pago anteriormente (para títulos parciais)
                valor_ja_pago = Decimal('0')
                if titulo.titu_aber == 'P':
                    baixas_anteriores = Bapatitulos.objects.using(banco).filter(
                        bapa_empr=titulo.titu_empr,
                        bapa_fili=titulo.titu_fili,
                        bapa_forn=titulo.titu_forn,
                        bapa_titu=titulo.titu_titu,
                        bapa_seri=titulo.titu_seri,
                        bapa_parc=titulo.titu_parc
                    ).aggregate(
                        total_valo_pago=models.Sum('bapa_valo_pago'),
                        total_sub_tota=models.Sum('bapa_sub_tota')
                    )
                    # Usar bapa_valo_pago como prioridade, se não existir usar bapa_sub_tota
                    valor_ja_pago = (baixas_anteriores['total_valo_pago'] or 
                                   baixas_anteriores['total_sub_tota'] or 
                                   Decimal('0'))
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Valores calculados - Título: {valor_titulo}, Já pago: {valor_ja_pago}, Novo pagamento: {valor_total_pago}")
                
                # Gerar próximo número de sequência
                ultimo_bapa = Bapatitulos.objects.using(banco).order_by('-bapa_sequ').first()
                proximo_sequ = (ultimo_bapa.bapa_sequ + 1) if ultimo_bapa else 1
                
                # Determinar tipo de baixa baseado no valor total (já pago + novo pagamento)
                valor_total_acumulado = valor_ja_pago + valor_total_pago
                if valor_total_acumulado >= valor_titulo:
                    tipo_baixa_final = 'T'  # Total
                else:
                    tipo_baixa_final = 'P'  # Parcial
                
                logger.info(f"Tipo de baixa determinado: {tipo_baixa_final}")
                
                # Criar registro de baixa
                baixa = Bapatitulos.objects.using(banco).create(
                    bapa_sequ=proximo_sequ,
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
                    bapa_valo_pago=valor_pago,  # Valor principal pago
                    bapa_sub_tota=valor_total_pago,  # Subtotal com juros/multa/desconto
                    bapa_topa=tipo_baixa_final,
                    bapa_form=data.get('forma_pagamento', 'B'),  # Forma de pagamento
                    bapa_banc=data.get('banco'),
                    bapa_cheq=data.get('cheque'),
                    bapa_hist=data.get('historico', f'Baixa do título {titulo.titu_titu} feita por Mobile'),
                    bapa_emis=titulo.titu_emis,
                    bapa_venc=titulo.titu_venc,
                    bapa_cont=titulo.titu_cont,
                    bapa_cecu=titulo.titu_cecu,
                    bapa_even=titulo.titu_even,
                    bapa_port=titulo.titu_port,
                    bapa_situ=titulo.titu_situ,
                 
                )
                
                # Atualizar status do título
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
                
                # Criar lançamento bancário se forma de pagamento for 'B' (Banco)
                if data.get('forma_pagamento') == 'B' and data.get('banco'):
                    historico_lancamento = f"Pagamento título {titulo.titu_titu} - {data.get('historico', 'Baixa via Mobile')}"
                    
                    try:
                        lancamento = criar_lancamento_bancario_baixa(
                            empresa=titulo.titu_empr,
                            filial=titulo.titu_fili,
                            banco_id=data.get('banco'),
                            valor=valor_total_pago,
                            historico=historico_lancamento,
                            entidade=titulo.titu_forn,
                            tipo_baixa='pagar',
                            banco_db=banco
                        )
                        logger.info(f"Lançamento bancário criado - ID: {lancamento.laba_ctrl}")
                    except Exception as e:
                        logger.error(f"Erro ao criar lançamento bancário: {str(e)}")
                        # Não falha a baixa por erro no lançamento
                
                logger.info(f"Baixa realizada com sucesso - ID: {baixa.bapa_sequ}")
                
                return Response({
                    'message': 'Título baixado com sucesso',
                    'baixa_id': baixa.bapa_sequ,
                    'valor_pago': valor_total_pago,
                    'status_titulo': tipo_baixa_final
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao baixar título {titulo.titu_titu}: {str(e)}")
            return Response(
                {'error': f'Erro ao baixar título: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
