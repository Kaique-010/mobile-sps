from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, F, Count
from django.core.cache import cache
from django.utils import timezone
from core.utils import get_licenca_db_config
from Produtos.models import Produtos, SaldoProduto
from coletaestoque.models import ColetaEstoque
from coletaestoque.serializers import ColetaEstoqueSerializer
from Produtos.serializers import ProdutoSerializer


class ColetaEstoqueViewSet(viewsets.ModelViewSet):
    serializer_class = ColetaEstoqueSerializer
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return ColetaEstoque.objects.using(banco).all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        context['empresa_id'] = self.request.headers.get('empresa-id', '1')
        return context

    @action(detail=False, methods=["get"], url_path='buscar-produto')
    def buscar_produto(self, request, slug=None):
        """Busca produto por código de barras (prod_coba)"""
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            codigo_barras = request.query_params.get("codigo", "").strip()
            
            if not codigo_barras:
                return Response({"error": "Código de barras é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

            # Busca produto pelo código de barras com múltiplas condições
            # Mesma lógica da view de Produtos para tratar códigos com e sem zeros
            produto = Produtos.objects.using(banco).filter(
                Q(prod_coba=codigo_barras) |
                Q(prod_coba=codigo_barras.lstrip("0")) |
                Q(prod_coba=codigo_barras.zfill(13)) |
                Q(prod_coba__icontains=codigo_barras)
            ).first()
            
            if not produto:
                return Response({"error": "Produto não encontrado"}, status=status.HTTP_404_NOT_FOUND)
            
            # Busca saldo atual
            saldo = SaldoProduto.objects.using(banco).filter(
                produto_codigo=produto.prod_codi
            ).first()
            
            data = {
                'prod_codi': produto.prod_codi,
                'prod_nome': produto.prod_nome,
                'prod_coba': produto.prod_coba,
                'saldo_atual': saldo.saldo_estoque if saldo else 0
            }
            
            return Response(data)
            
        except Exception as e:
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)

    @action(detail=False, methods=["post"], url_path='registrar-leitura')
    def registrar_leitura(self, request, slug=None):
        """Registra uma nova leitura de estoque"""
        try:
            banco = get_licenca_db_config(self.request)
            codigo_barras = request.data.get('codigo_barras')
            quantidade = request.data.get('quantidade', 1)
            usuario_id = request.data.get('usuario_id')
            
            if not codigo_barras:
                return Response({"error": "Código de barras é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Busca produto
            produto = Produtos.objects.using(banco).filter(prod_coba=codigo_barras).first()
            if not produto:
                return Response({"error": "Produto não encontrado"}, status=status.HTTP_404_NOT_FOUND)
            
            # Obtém empresa e filial dos headers
            empresa = int(self.request.headers.get("X-Empresa", 1))
            filial = int(self.request.headers.get("X-Filial", 1))
            
            # Cria registro de coleta
            data = {
                'cole_prod': produto.prod_codi,
                'cole_quan_lida': quantidade,
                'cole_usua': usuario_id,
                'cole_empr': empresa,
                'cole_fili': filial
            }
            
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)

    @action(detail=False, methods=["get"], url_path='resumo-coletas')
    def resumo_coletas(self, request, slug=None):
        """Retorna resumo das coletas agrupadas por produto"""
        try:
            banco = get_licenca_db_config(self.request)
            empresa = int(self.request.headers.get("X-Empresa", 1))
            filial = int(self.request.headers.get("X-Filial", 1))
            
            # Agrupa coletas por produto
            coletas = ColetaEstoque.objects.using(banco).filter(
                cole_empr=empresa,
                cole_fili=filial
            ).values(
                'cole_prod'
            ).annotate(
                total_coletado=Sum('cole_quan_lida'),
                total_leituras=Count('id')
            )
            
            resumo = []
            for coleta in coletas:
                produto = Produtos.objects.using(banco).filter(
                    prod_codi=coleta['cole_prod']
                ).first()
                
                if produto:
                    resumo.append({
                        'cole_prod__prod_codi': produto.prod_codi,
                        'cole_prod__prod_nome': produto.prod_nome,
                        'cole_prod__prod_coba': produto.prod_coba,
                        'total_coletado': coleta['total_coletado'],
                        'total_leituras': coleta['total_leituras']
                    })
            
            resumo.sort(key=lambda x: x['cole_prod__prod_nome'])
            
            return Response(list(resumo))
            
        except Exception as e:
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)

    @action(detail=False, methods=["post"], url_path='atualizar-estoque')
    def atualizar_estoque(self, request, slug=None):
        """Atualiza saldo de estoque baseado nas coletas"""
        try:
            banco = get_licenca_db_config(self.request)
            empresa = int(self.request.headers.get("X-Empresa", 1))
            filial = int(self.request.headers.get("X-Filial", 1))
            
            # Busca todas as coletas não processadas
            coletas = ColetaEstoque.objects.using(banco).filter(
                cole_empr=empresa,
                cole_fili=filial,
                cole_processado=False
            )
            
            # Agrupa por produto
            resumo_coletas = coletas.values('cole_prod').annotate(
                total_coletado=Sum('cole_quan_lida')
            )
            
            atualizados = []
            
            for item in resumo_coletas:
                produto_codigo = item['cole_prod']
                quantidade_coletada = item['total_coletado']
                
                # Atualiza saldo
                saldo, created = SaldoProduto.objects.using(banco).get_or_create(
                    produto_codigo_id=produto_codigo,
                    empresa=empresa,
                    filial=filial,
                    defaults={'saldo_estoque': quantidade_coletada}
                )
                
                if not created:
                    saldo.saldo_estoque = quantidade_coletada
                    saldo.save(using=banco)
                
                atualizados.append({
                    'produto': produto_codigo,
                    'novo_saldo': quantidade_coletada
                })
            
            # Marca coletas como processadas
            coletas.update(
                cole_processado=True,
                cole_data_processamento=timezone.now()
            )
            
            return Response({
                'message': f'{len(atualizados)} produtos atualizados',
                'produtos_atualizados': atualizados
            })
            
        except Exception as e:
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)