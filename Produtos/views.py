from xml.dom import ValidationErr
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
import re
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.http import Http404
from django.db.models import Sum
from rest_framework.generics import ListAPIView
from django.db.models import Q, Subquery, OuterRef, DecimalField, Value as V, CharField
from django.db.models.functions import Coalesce, Cast
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from .models import Produtos, SaldoProduto, Tabelaprecos, UnidadeMedida, Tabelaprecoshist, ProdutosDetalhados
from .serializers import ProdutoSerializer, TabelaPrecoSerializer, UnidadeMedidaSerializer, ProdutoDetalhadoSerializer
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.core.cache import cache


class UnidadeMedidaListView(ModuloRequeridoMixin, ListAPIView):
    modulo_necessario = 'Produtos'
    serializer_class = UnidadeMedidaSerializer
    
    def get(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
            
        banco = get_licenca_db_config(self.request)
        
        if banco:
            # Cache para unidades de medida
            cache_key = f"unidades_medida_{banco}"
            queryset = cache.get(cache_key)
            
            if not queryset:
                queryset = list(UnidadeMedida.objects.using(banco).all().order_by('unid_desc'))
                cache.set(cache_key, queryset, 1800)  # Cache por 30 minutos
                
            serializer = UnidadeMedidaSerializer(queryset, many=True)
            return Response(serializer.data)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context


class ProdutoListView(ModuloRequeridoMixin, APIView):
    modulo_necessario = 'Produtos'
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banco = get_licenca_db_config(self.request)

        if not banco:
            return Response({"error": "Banco não encontrado."}, status=400)

        saldo_subquery = Subquery(
            SaldoProduto.objects.using(banco).filter(
                produto_codigo=OuterRef('pk')
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )

        queryset = Produtos.objects.using(banco).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField())
        ).order_by('-prod_codi')[:100]  
    
        serializer = ProdutoSerializer(queryset, many=True, context={'banco': banco})
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
        
        
class ProdutoViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    permission_classes = [IsAuthenticated]
    serializer_class = ProdutoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']
    filterset_fields = ['prod_empr']
    
    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            raise Http404("Banco de dados não encontrado")
        
        # Verificar se é URL com chave composta
        if 'empresa' in self.kwargs and 'codigo' in self.kwargs:
            empresa = self.kwargs['empresa']
            codigo = self.kwargs['codigo']
        else:
            # Fallback para lookup padrão
            lookup_value = self.kwargs.get(self.lookup_field)
            empresa = self.request.query_params.get('prod_empr')
            codigo = lookup_value
        
        if not empresa or not codigo:
            raise Http404("Empresa e código do produto são obrigatórios")
        
        try:
            queryset = self.get_queryset().filter(
                prod_empr=empresa,
                prod_codi=codigo
            )
            
            obj = queryset.first()
            if not obj:
                raise Http404(f"Produto {codigo} não encontrado para empresa {empresa}")
                
            self.check_object_permissions(self.request, obj)
            return obj
            
        except Exception as e:
            raise Http404(f"Erro ao buscar produto: {str(e)}")
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)

        if not banco:
            return Produtos.objects.none()

        # Otimizar subqueries - CORRIGIDO com empresa e filial
        empresa_id = self.request.query_params.get('prod_empr') or self.request.META.get('HTTP_X_EMPRESA', 1)
        filial_id = self.request.query_params.get('prod_fili') or self.request.META.get('HTTP_X_FILIAL', 1)
        
        saldo_subquery = Subquery(
            SaldoProduto.objects.using(banco).filter(
                produto_codigo=OuterRef('pk'),
                empresa=empresa_id,
                filial=filial_id
            ).values('saldo_estoque')[:1],
            output_field=DecimalField()
        )
        
        preco_vista_subquery = Subquery(
            Tabelaprecos.objects.using(banco).filter(
                tabe_prod=OuterRef('prod_codi'),
                tabe_empr=OuterRef('prod_empr')
            ).exclude(
                tabe_entr__year__lt=1900
            ).exclude(
                tabe_entr__year__gt=2100
            ).values('tabe_avis')[:1],
            output_field=DecimalField()
        )

        preco_normal_subquery = Subquery(
            Tabelaprecos.objects.using(banco).filter(
                tabe_prod=OuterRef('prod_codi'),
                tabe_empr=OuterRef('prod_empr')
            ).exclude(
                tabe_entr__year__lt=1900
            ).exclude(
                tabe_entr__year__gt=2100
            ).values('tabe_prco')[:1],
            output_field=DecimalField()
        )

        queryset = Produtos.objects.using(banco).annotate(
            saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
            prod_preco_vista=Coalesce(preco_vista_subquery, V(0), output_field=DecimalField()),
            prod_preco_normal=Coalesce(preco_normal_subquery, V(0), output_field=DecimalField())
        )
        
        # Aplicar filtros de forma otimizada
        empresa_id = self.request.query_params.get('prod_empr')
        if empresa_id:
            queryset = queryset.filter(prod_empr=empresa_id)
            
        return queryset.order_by('prod_empr', 'prod_codi')

    @action(detail=False, methods=["get"])
    def busca(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            banco = get_licenca_db_config(self.request)

            q = request.query_params.get("q", "").strip()
            
            if not q:
                return Response([], status=200)

            # Cache para buscas frequentes
            cache_key = f"produto_busca_{banco}_{q}"
            cached_result = cache.get(cache_key)
            
            if cached_result:
                return Response(cached_result)

            # Otimizar subqueries (mesmo código anterior)
            saldo_subquery = Subquery(
                SaldoProduto.objects.using(banco).filter(
                    produto_codigo=OuterRef('pk')
                ).values('saldo_estoque')[:1],
                output_field=DecimalField()
            )

            preco_vista_subquery = Subquery(
                Tabelaprecos.objects.using(banco).filter(
                    tabe_prod=OuterRef('prod_codi'),
                    tabe_empr=OuterRef('prod_empr')
                ).exclude(
                    tabe_entr__year__lt=1900
                ).exclude(
                    tabe_entr__year__gt=2100
                ).values('tabe_avis')[:1],
                output_field=DecimalField()
            )

            preco_normal_subquery = Subquery(
                Tabelaprecos.objects.using(banco).filter(
                    tabe_prod=OuterRef('prod_codi'),
                    tabe_empr=OuterRef('prod_empr')
                ).exclude(
                    tabe_entr__year__lt=1900
                ).exclude(
                    tabe_entr__year__gt=2100
                ).values('tabe_prco')[:1],
                output_field=DecimalField()
            )

            produtos = Produtos.objects.using(banco).annotate(
                saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
                prod_preco_vista=Coalesce(preco_vista_subquery, V(0), output_field=DecimalField()),
                prod_preco_normal=Coalesce(preco_normal_subquery, V(0), output_field=DecimalField()),
                prod_coba_str=Coalesce(Cast('prod_coba', CharField()), V(''))
            ).filter(
                Q(prod_nome__icontains=q) |
                Q(prod_coba_str__icontains=q) |
                Q(prod_codi__icontains=q.lstrip("0"))  
            )[:50]  # Limitar resultados

            serializer = self.get_serializer(produtos, many=True)
            result_data = serializer.data
            
            # Cache por 5 minutos
            cache.set(cache_key, result_data, 300)
            
            return Response(result_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        precos_data = request.data.pop('precos', None)
        
        serializer = self.get_serializer(
            data=request.data, 
            context={'banco': banco, 'precos_data': precos_data}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response(
                {"detail": "Banco de dados não especificado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance = self.get_object()
        precos_data = request.data.pop('precos', None)
        
        # Atualizar produto primeiro
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.pop('partial', False),
            context={'banco': banco}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Se tiver dados de preço, atualizar a tabela de preços
        if precos_data:
            try:
                # Buscar registro de preço existente
                preco = Tabelaprecos.objects.using(banco).get(
                    tabe_prod=instance.prod_codi,
                    tabe_empr=instance.prod_empr,
                    tabe_fili=1  # Filial padrão
                )
                
                # Guardar valores antigos
                old_values = {
                    'tabe_prco': preco.tabe_prco,
                    'tabe_avis': preco.tabe_avis,
                    'tabe_apra': preco.tabe_apra,
                    'tabe_pipi': preco.tabe_pipi,
                    'tabe_fret': preco.tabe_fret,
                    'tabe_desp': preco.tabe_desp,
                    'tabe_cust': preco.tabe_cust,
                    'tabe_cuge': preco.tabe_cuge,
                    'tabe_icms': preco.tabe_icms,
                    'tabe_impo': preco.tabe_impo,
                    'tabe_marg': preco.tabe_marg,
                    'tabe_praz': preco.tabe_praz,
                    'tabe_valo_st': preco.tabe_valo_st,
                }
                
                # Criar histórico
                historico = "Alteração de preços via API"
                if 'tabe_prco' in precos_data and precos_data['tabe_prco'] != old_values['tabe_prco']:
                    historico += f"\nPreço Normal: R$ {old_values['tabe_prco'] or 0:.2f} -> R$ {precos_data['tabe_prco']:.2f}"
                if 'tabe_avis' in precos_data and precos_data['tabe_avis'] != old_values['tabe_avis']:
                    historico += f"\nPreço à Vista: R$ {old_values['tabe_avis'] or 0:.2f} -> R$ {precos_data['tabe_avis']:.2f}"
                if 'tabe_apra' in precos_data and precos_data['tabe_apra'] != old_values['tabe_apra']:
                    historico += f"\nPreço a Prazo: R$ {old_values['tabe_apra'] or 0:.2f} -> R$ {precos_data['tabe_apra']:.2f}"

                # Salvar histórico
                hist_data = {
                    'tabe_empr': instance.prod_empr,
                    'tabe_fili': 1,  # Filial padrão
                    'tabe_prod': instance.prod_codi,
                    'tabe_data_hora': timezone.now(),
                    'tabe_hist': historico,
                    'tabe_perc_reaj': precos_data.get('tabe_perc_reaj'),
                    # Valores anteriores
                    'tabe_prco_ante': old_values['tabe_prco'],
                    'tabe_avis_ante': old_values['tabe_avis'],
                    'tabe_apra_ante': old_values['tabe_apra'],
                    'tabe_pipi_ante': old_values['tabe_pipi'],
                    'tabe_fret_ante': old_values['tabe_fret'],
                    'tabe_desp_ante': old_values['tabe_desp'],
                    'tabe_cust_ante': old_values['tabe_cust'],
                    'tabe_cuge_ante': old_values['tabe_cuge'],
                    'tabe_icms_ante': old_values['tabe_icms'],
                    'tabe_impo_ante': old_values['tabe_impo'],
                    'tabe_marg_ante': old_values['tabe_marg'],
                    'tabe_praz_ante': old_values['tabe_praz'],
                    'tabe_valo_st_ante': old_values['tabe_valo_st'],
                    # Novos valores
                    'tabe_prco_novo': precos_data.get('tabe_prco'),
                    'tabe_avis_novo': precos_data.get('tabe_avis'),
                    'tabe_apra_novo': precos_data.get('tabe_apra'),
                    'tabe_pipi_novo': precos_data.get('tabe_pipi'),
                    'tabe_fret_novo': precos_data.get('tabe_fret'),
                    'tabe_desp_novo': precos_data.get('tabe_desp'),
                    'tabe_cust_novo': precos_data.get('tabe_cust'),
                    'tabe_cuge_novo': precos_data.get('tabe_cuge'),
                    'tabe_icms_novo': precos_data.get('tabe_icms'),
                    'tabe_impo_novo': precos_data.get('tabe_impo'),
                    'tabe_marg_novo': precos_data.get('tabe_marg'),
                    'tabe_praz_novo': precos_data.get('tabe_praz'),
                    'tabe_valo_st_novo': precos_data.get('tabe_valo_st'),
                }
                
                # Criar registro de histórico
                Tabelaprecoshist.objects.using(banco).create(**hist_data)

                # Atualizar preços
                preco_serializer = TabelaPrecoSerializer(preco, data=precos_data, partial=True, context={'banco': banco})
                preco_serializer.is_valid(raise_exception=True)
                preco_serializer.save()

            except Tabelaprecos.DoesNotExist:
                # Se não existir, criar novo registro de preço
                precos_data.update({
                    'tabe_empr': instance.prod_empr,
                    'tabe_fili': 1,  # Filial padrão
                    'tabe_prod': instance.prod_codi
                })
                preco_serializer = TabelaPrecoSerializer(data=precos_data, context={'banco': banco})
                preco_serializer.is_valid(raise_exception=True)
                preco_serializer.save()

        # Buscar o objeto atualizado usando chave composta
        banco = get_licenca_db_config(self.request)
        instance = Produtos.objects.using(banco).get(
            prod_codi=instance.prod_codi,
            prod_empr=instance.prod_empr
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    @action(detail=True, methods=['get'])
    def precos(self, request, pk=None):
        produto = self.get_object()
        banco = get_licenca_db_config(request)
        
        precos = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=produto.prod_codi,
            tabe_empr=produto.prod_empr
        )
        
        serializer = TabelaPrecoSerializer(precos, many=True, context={'banco': banco})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def atualizar_precos(self, request, pk=None):
        produto = self.get_object()
        banco = get_licenca_db_config(request)
        
        serializer = TabelaPrecoSerializer(
            data=request.data,
            context={'banco': banco}
        )
        
        if serializer.is_valid():
            try:
                preco = Tabelaprecos.objects.using(banco).get(
                    tabe_prod=produto.prod_codi,
                    tabe_empr=produto.prod_empr,
                    tabe_fili=request.data.get('tabe_fili', 1)
                )
                serializer.update(preco, serializer.validated_data)
            except Tabelaprecos.DoesNotExist:
                serializer.save(
                    tabe_prod=produto.prod_codi,
                    tabe_empr=produto.prod_empr,
                    tabe_fili=request.data.get('tabe_fili', 1)
                )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TabelaPrecoMobileViewSet(viewsets.ModelViewSet):
    serializer_class = TabelaPrecoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['tabe_empr', 'tabe_fili', 'tabe_prod']
    search_fields = ['tabe_prod']
    lookup_field = 'chave_composta'
    lookup_value_regex = '[^/]+'

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Tabelaprecos.objects.none()
        
        queryset = Tabelaprecos.objects.using(banco)
        
        # Filtrar por empresa se fornecido
        empresa = self.request.query_params.get('empresa')
        if empresa:
            queryset = queryset.filter(tabe_empr=empresa)
            
        # Filtrar por filial se fornecido
        filial = self.request.query_params.get('filial')
        if filial:
            queryset = queryset.filter(tabe_fili=filial)
            
        # Filtrar por produto se fornecido
        produto = self.request.query_params.get('produto')
        if produto:
            queryset = queryset.filter(tabe_prod=produto)
            
        return queryset

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response(
                {"detail": "Banco de dados não especificado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Processar percentuais se fornecidos
        if 'percentual_avis' in request.data and 'tabe_prco' in request.data:
            preco_base = float(request.data['tabe_prco'])
            percentual = float(request.data.pop('percentual_avis'))
            request.data['tabe_avis'] = round(preco_base * (1 + percentual / 100), 2)

        if 'percentual_apra' in request.data and 'tabe_prco' in request.data:
            preco_base = float(request.data['tabe_prco'])
            percentual = float(request.data.pop('percentual_apra'))
            request.data['tabe_apra'] = round(preco_base * (1 + percentual / 100), 2)

        # Remover campos virtuais antes da criação
        create_data = {k: v for k, v in request.data.items() 
                      if k in [f.name for f in Tabelaprecos._meta.fields]}

        # Criar o registro
        instance = Tabelaprecos.objects.using(banco).create(**create_data)
        
        # Criar histórico
        hist_data = {
            'tabe_empr': instance.tabe_empr,
            'tabe_fili': instance.tabe_fili,
            'tabe_prod': instance.tabe_prod,
            'tabe_data_hora': timezone.now(),
            'tabe_hist': "Criação de preços via API",
            'tabe_perc_reaj': request.data.get('tabe_perc_reaj'),
            'tabe_prco_novo': instance.tabe_prco,
            'tabe_avis_novo': instance.tabe_avis,
            'tabe_apra_novo': instance.tabe_apra,
        }
        
        Tabelaprecoshist.objects.using(banco).create(**hist_data)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_object(self):
        # Extrair os componentes da chave composta
        chave = self.kwargs['chave_composta'].split('-')
        if len(chave) != 3:
            raise ValidationError("Formato de chave inválido")
        
        empresa, filial, produto = chave
        
        # Buscar o objeto
        queryset = self.get_queryset().filter(
            tabe_empr=empresa,
            tabe_fili=filial,
            tabe_prod=produto
        )
        
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response(
                {"detail": "Banco de dados não especificado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance = self.get_object()
        
        # Guardar valores antigos
        old_values = {
            'tabe_prco': instance.tabe_prco,
            'tabe_avis': instance.tabe_avis,
            'tabe_apra': instance.tabe_apra,
            'tabe_pipi': instance.tabe_pipi,
            'tabe_fret': instance.tabe_fret,
            'tabe_desp': instance.tabe_desp,
            'tabe_cust': instance.tabe_cust,
            'tabe_cuge': instance.tabe_cuge,
            'tabe_icms': instance.tabe_icms,
            'tabe_impo': instance.tabe_impo,
            'tabe_marg': instance.tabe_marg,
            'tabe_praz': instance.tabe_praz,
            'tabe_valo_st': instance.tabe_valo_st,
        }

        # Processar percentuais se fornecidos
        if 'percentual_avis' in request.data and 'tabe_prco' in request.data:
            preco_base = float(request.data['tabe_prco'])
            percentual = float(request.data.pop('percentual_avis'))
            request.data['tabe_avis'] = round(preco_base * (1 + percentual / 100), 2)

        if 'percentual_apra' in request.data and 'tabe_prco' in request.data:
            preco_base = float(request.data['tabe_prco'])
            percentual = float(request.data.pop('percentual_apra'))
            request.data['tabe_apra'] = round(preco_base * (1 + percentual / 100), 2)
        
        # Criar histórico
        historico = "Alteração de preços via API"
        if 'tabe_prco' in request.data and request.data['tabe_prco'] != old_values['tabe_prco']:
            historico += f"\nPreço Normal: R$ {old_values['tabe_prco'] or 0:.2f} -> R$ {request.data['tabe_prco']:.2f}"
        if 'tabe_avis' in request.data and request.data['tabe_avis'] != old_values['tabe_avis']:
            historico += f"\nPreço à Vista: R$ {old_values['tabe_avis'] or 0:.2f} -> R$ {request.data['tabe_avis']:.2f}"
        if 'tabe_apra' in request.data and request.data['tabe_apra'] != old_values['tabe_apra']:
            historico += f"\nPreço a Prazo: R$ {old_values['tabe_apra'] or 0:.2f} -> R$ {request.data['tabe_apra']:.2f}"

        # Salvar histórico
        hist_data = {
            'tabe_empr': instance.tabe_empr,
            'tabe_fili': instance.tabe_fili,
            'tabe_prod': instance.tabe_prod,
            'tabe_data_hora': timezone.now(),
            'tabe_hist': historico,
            'tabe_perc_reaj': request.data.get('tabe_perc_reaj'),
            # Valores anteriores
            'tabe_prco_ante': old_values['tabe_prco'],
            'tabe_avis_ante': old_values['tabe_avis'],
            'tabe_apra_ante': old_values['tabe_apra'],
            'tabe_pipi_ante': old_values['tabe_pipi'],
            'tabe_fret_ante': old_values['tabe_fret'],
            'tabe_desp_ante': old_values['tabe_desp'],
            'tabe_cust_ante': old_values['tabe_cust'],
            'tabe_cuge_ante': old_values['tabe_cuge'],
            'tabe_icms_ante': old_values['tabe_icms'],
            'tabe_impo_ante': old_values['tabe_impo'],
            'tabe_marg_ante': old_values['tabe_marg'],
            'tabe_praz_ante': old_values['tabe_praz'],
            'tabe_valo_st_ante': old_values['tabe_valo_st'],
            # Novos valores
            'tabe_prco_novo': request.data.get('tabe_prco'),
            'tabe_avis_novo': request.data.get('tabe_avis'),
            'tabe_apra_novo': request.data.get('tabe_apra'),
            'tabe_pipi_novo': request.data.get('tabe_pipi'),
            'tabe_fret_novo': request.data.get('tabe_fret'),
            'tabe_desp_novo': request.data.get('tabe_desp'),
            'tabe_cust_novo': request.data.get('tabe_cust'),
            'tabe_cuge_novo': request.data.get('tabe_cuge'),
            'tabe_icms_novo': request.data.get('tabe_icms'),
            'tabe_impo_novo': request.data.get('tabe_impo'),
            'tabe_marg_novo': request.data.get('tabe_marg'),
            'tabe_praz_novo': request.data.get('tabe_praz'),
            'tabe_valo_st_novo': request.data.get('tabe_valo_st'),
        }
        
        # Criar registro de histórico
        Tabelaprecoshist.objects.using(banco).create(**hist_data)

        # Remover campos virtuais antes do update
        update_data = {k: v for k, v in request.data.items() 
                      if k in [f.name for f in Tabelaprecos._meta.fields]}

        # Atualizar a tabela de preços usando update direto
        Tabelaprecos.objects.using(banco).filter(
            tabe_empr=instance.tabe_empr,
            tabe_fili=instance.tabe_fili,
            tabe_prod=instance.tabe_prod
        ).update(**update_data)

        # Buscar o objeto atualizado usando a chave composta
        updated_instance = Tabelaprecos.objects.using(banco).get(
            tabe_empr=instance.tabe_empr,
            tabe_fili=instance.tabe_fili,
            tabe_prod=instance.tabe_prod
        )
        serializer = self.get_serializer(updated_instance)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context




class ProdutosDetalhadosViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    serializer_class = ProdutoDetalhadoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['codigo', 'nome', 'marca_nome']
    search_fields = ['codigo', 'nome', 'marca_nome']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self, slug=None):
        slug = get_licenca_slug()
        qs = ProdutosDetalhados.objects.using(slug).all()

        if marca_nome := self.request.query_params.get('marca_nome'):
            if marca_nome == '__sem_marca__':
                qs = qs.filter(Q(marca_nome__isnull=True) | Q(marca_nome=''))
            else:
                qs = qs.filter(marca_nome=marca_nome)


        # Filtros de estoque (ajustados para corresponder ao frontend)
        com_saldo = self.request.query_params.get('com_saldo')
        sem_saldo = self.request.query_params.get('sem_saldo')
        estoque_minimo = self.request.query_params.get('estoque_minimo')  
        
        if com_saldo == 'true':
            qs = qs.filter(saldo__gt=0)
        elif sem_saldo == 'true':
            qs = qs.filter(saldo=0)
        elif estoque_minimo == 'true':
            qs = qs.filter(saldo__lt=F('estoque_minimo'))

        return qs



class EstoqueResumoView(APIView):
    permission_classes = [IsAuthenticated]
    modulo_necessario = 'dash'

    def get(self, request, *args, **kwargs):
        slug = get_licenca_slug()
        qs = ProdutosDetalhados.objects.using(slug).all()

        # Filtros opcionais
        marca = request.query_params.get('marca')
        grupo = request.query_params.get('grupo')
        empresa = request.query_params.get('empresa')
        filial = request.query_params.get('filial')

        if marca == '__sem_marca__':
            qs = qs.filter(marca_nome__isnull=True)
        elif marca:
            qs = qs.filter(marca_nome=marca)

        if grupo:
            qs = qs.filter(grupo_id=grupo)

        if empresa:
            qs = qs.filter(empresa=empresa)

        if filial:
            qs = qs.filter(filial=filial)

        resumo = qs.aggregate(
            total_estoque=Sum('valor_total_estoque'),
            total_a_vista=Sum('valor_total_venda_vista'),
            total_prazo=Sum('valor_total_venda_prazo'),
        )

        return Response({
            'total_estoque': float(resumo['total_estoque'] or 0),
            'total_a_vista': float(resumo['total_a_vista'] or 0),
            'total_prazo': float(resumo['total_prazo'] or 0),
        })
