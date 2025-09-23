import logging
from django.db import transaction
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from .models import NotaFiscal
from .serializers import NotaFiscalSerializer, NotaFiscalListSerializer
from Entidades.models import Entidades
from Licencas.models import Empresas
from core.utils import get_licenca_db_config

logger = logging.getLogger('NotasFiscais')


class NotaFiscalViewSet(viewsets.ModelViewSet):
    serializer_class = NotaFiscalSerializer
    lookup_field = 'numero_nota_fiscal'
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = [
        'numero_nota_fiscal', 
        'chave_acesso', 
        'emitente_razao_social', 
        'destinatario_razao_social',
        'natureza_operacao'
    ]
    filterset_fields = [
        'empresa', 
        'filial', 
        'numero_nota_fiscal', 
        'serie', 
        'modelo',
        'data_emissao', 
        'status_nfe', 
        'cancelada', 
        'ambiente',
        'tipo_operacao',
        'cliente',
        'vendedor'
    ]

    def get_object(self):
        """
        Obtém o objeto nota fiscal usando chave composta empresa/filial/numero
        """
        try:
            # Priorizar parâmetros da URL (self.kwargs) primeiro
            empresa = self.kwargs.get('empresa') or self.kwargs.get('empresa_id')
            filial = self.kwargs.get('filial') or self.kwargs.get('filial_id') 
            numero = self.kwargs.get('numero') or self.kwargs.get('numero_nota_fiscal')
            
            # Se não encontrou na URL, tentar query_params como fallback
            if not empresa:
                empresa = self.request.query_params.get('empresa') or self.request.query_params.get('empresa_id')
            if not filial:
                filial = self.request.query_params.get('filial') or self.request.query_params.get('filial_id')
            if not numero:
                numero = self.request.query_params.get('numero') or self.request.query_params.get('numero_nota_fiscal')
                
            # Se ainda não encontrou, tentar request.data como último recurso
            if not empresa and hasattr(self.request, 'data'):
                empresa = self.request.data.get('empresa') or self.request.data.get('empresa_id')
            if not filial and hasattr(self.request, 'data'):
                filial = self.request.data.get('filial') or self.request.data.get('filial_id')
            if not numero and hasattr(self.request, 'data'):
                numero = self.request.data.get('numero') or self.request.data.get('numero_nota_fiscal')

            if not all([empresa, filial, numero]):
                raise ValidationError({
                    'error': 'Parâmetros obrigatórios: empresa, filial e numero'
                })

            # Obter configuração do banco
            banco = get_licenca_db_config(self.request)
            if not banco:
                raise NotFound(f"Configuração de banco não encontrada")

            # Buscar a nota fiscal
            nota_fiscal = NotaFiscal.objects.using(banco).filter(
                empresa=empresa,
                filial=filial,
                numero_nota_fiscal=numero
            ).first()

            if not nota_fiscal:
                raise NotFound(f"Nota fiscal não encontrada: {empresa}/{filial}/{numero}")

            return nota_fiscal

        except Exception as e:
            logger.error(f"Erro ao buscar nota fiscal: {e}")
            if isinstance(e, (NotFound, ValidationError)):
                raise
            raise ValidationError({'error': f'Erro interno: {str(e)}'})

    def get_queryset(self):
        """
        Retorna queryset filtrado por empresa/filial com otimizações
        """
        try:
            # Usar get_licenca_db_config para obter banco do slug
            banco = get_licenca_db_config(self.request)
            if not banco:
                logger.warning("Banco não encontrado via slug")
                return NotaFiscal.objects.none()

            # Buscar todas as notas fiscais do banco
            queryset = NotaFiscal.objects.using(banco).all()
            
            # Filtro por empresa se fornecido
            empresa = (
                self.kwargs.get('empresa') or 
                self.request.query_params.get('empresa') or
                self.request.query_params.get('empresa_id')
            )
            if empresa:
                queryset = queryset.filter(empresa=empresa)
            
            # Filtro por filial se fornecido
            filial = (
                self.kwargs.get('filial') or 
                self.request.query_params.get('filial') or
                self.request.query_params.get('filial_id')
            )
            if filial:
                queryset = queryset.filter(filial=filial)

            # Ordenação padrão
            queryset = queryset.order_by('-data_emissao', '-numero_nota_fiscal')

            logger.info(f"Queryset gerado para banco {banco}: {queryset.count()} registros")
            return queryset

        except Exception as e:
            logger.error(f"Erro no get_queryset: {e}")
            return NotaFiscal.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def list(self, request, *args, **kwargs):
        """
        Lista notas fiscais com serializer otimizado
        """
        try:
            # Usar serializer simplificado para listagem
            queryset = self.filter_queryset(self.get_queryset())
            
            # Paginação
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = NotaFiscalListSerializer(
                    page, 
                    many=True, 
                    context=self.get_serializer_context()
                )
                return self.get_paginated_response(serializer.data)

            serializer = NotaFiscalListSerializer(
                queryset, 
                many=True, 
                context=self.get_serializer_context()
            )
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Erro na listagem de notas fiscais: {e}")
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        """
        Recupera uma nota fiscal específica
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Erro ao recuperar nota fiscal: {e}")
            if isinstance(e, (NotFound, ValidationError)):
                raise
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def xml_nfe(self, request, numero_nota_fiscal=None, empresa=None, filial=None, numero=None, slug=None):
        """
        Retorna o XML da NFe
        """
        try:
            nota_fiscal = self.get_object()
            if not nota_fiscal.xml_nfe:
                return Response(
                    {'error': 'XML não disponível para esta nota fiscal'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({
                'xml_nfe': nota_fiscal.xml_nfe,
                'protocolo': nota_fiscal.protocolo_nfe,
                'status': nota_fiscal.status_nfe
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar XML da NFe: {e}")
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def danfe(self, request, numero_nota_fiscal=None, empresa=None, filial=None, numero=None, slug=None):
        """
        Gera e retorna o DANFE em PDF da NFe
        """
        try:
            nota_fiscal = self.get_object()
            if not nota_fiscal.xml_nfe:
                return Response(
                    {'error': 'XML não disponível para gerar DANFE'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Gerar PDF do DANFE
            pdf_content = self._gerar_danfe_pdf(nota_fiscal.xml_nfe)
            
            if not pdf_content:
                return Response(
                    {'error': 'Erro ao gerar DANFE'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Retornar PDF como resposta
            from django.http import HttpResponse
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="danfe_{nota_fiscal.numero_nota_fiscal}.pdf"'
            return response
            
        except Exception as e:
            logger.error(f"Erro ao gerar DANFE: {e}")
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _gerar_danfe_pdf(self, xml_content):
        """
        Gera um PDF do DANFE a partir do XML da NFe usando brazilfiscalreport (padrão oficial)
        """
        try:
            from brazilfiscalreport.danfe import Danfe
            from io import BytesIO
            
            # Criar buffer para o PDF
            buffer = BytesIO()
            
            # Gerar DANFE usando a biblioteca oficial
            danfe = Danfe(xml=xml_content)
            danfe.output(buffer)
            
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"Erro ao gerar DANFE: {str(e)}")

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Retorna dados para dashboard de notas fiscais
        """
        try:
            queryset = self.get_queryset()
            
            # Estatísticas básicas
            total_notas = queryset.count()
            autorizadas = queryset.filter(status_nfe=100).count()
            canceladas = queryset.filter(cancelada=True).count()
            pendentes = queryset.exclude(status_nfe=100).exclude(cancelada=True).count()
            
            # Valor total
            from django.db.models import Sum
            valor_total = queryset.aggregate(
                total=Sum('valor_total_nota')
            )['total'] or 0
            
            return Response({
                'total_notas': total_notas,
                'autorizadas': autorizadas,
                'canceladas': canceladas,
                'pendentes': pendentes,
                'valor_total': valor_total,
            })
            
        except Exception as e:
            logger.error(f"Erro no dashboard: {e}")
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
