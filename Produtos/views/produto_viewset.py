import logging
logger = logging.getLogger(__name__)
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from rest_framework.exceptions import NotFound
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from core.decorator import ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from core.utils import get_ncm_master_db

from ..models import Ncm, Produtos, Tabelaprecos, UnidadeMedida, Lote, SaldoProduto
from ..preco_models import TabelaprecosPromocional, TabelaprecosPromocionalhist
from ..serializers.produto_serializer import ProdutoSerializer, ProdutoServicoSerializer
from ..serializers.tabela_preco_serializer import (
    TabelaPrecoPromocionalHistSerializer,
    TabelaPrecoPromocionalSerializer,
    TabelaPrecoSerializer,
)
from ..consultas.produto_consultas import listar_produtos, buscar_produto_por_codigo
from ..servicos.produto_servico import buscar_produto_por_hash
from ..servicos.etiqueta_servico import gerar_dados_etiquetas
from ..servicos.preco_servico import atualizar_preco_com_historico, criar_preco_com_historico
from ..servicos.preco_promocional import (
    atualizar_preco_com_historico as atualizar_preco_promocional_com_historico,
    criar_preco_com_historico as criar_preco_promocional_com_historico,
)

class ProdutoListView(ModuloRequeridoMixin, APIView):
    """
    View para listagem otimizada de produtos com saldo e preços.
    """
    modulo_necessario = 'Produtos'

    def get(self, request):
        banco = get_licenca_db_config(request)
        
        # Filtros
        q = request.query_params.get('q')
        marca_nome = request.query_params.get('marca')
        saldo_filter = request.query_params.get('saldo')
        limit = int(request.query_params.get('limit', 50))
        
        # Parâmetros de contexto
        empresa_id = request.headers.get('X-Empresa') or request.session.get('empresa_id')
        filial_id = request.headers.get('X-Filial') or request.session.get('filial_id')
       
        queryset = listar_produtos(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id,
            q=q,
            marca_nome=marca_nome,
            saldo_filter=saldo_filter,
            limit=limit
        )
        logger.info(f"Listar produtos com filtro: q={q}, marca={marca_nome}, saldo={saldo_filter}, limit={limit}")
        serializer = ProdutoSerializer(queryset, many=True, context={'banco': banco})
        return Response(serializer.data)


class ProdutoViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'Produtos'
    serializer_class = ProdutoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['prod_nome', 'prod_codi', 'prod_coba']
    filterset_fields = ['prod_empr']

    def _empresa_id(self, request):
        return (
            request.query_params.get('prod_empr')
            or request.query_params.get('empresa')
            or request.headers.get('X-Empresa')
            or request.session.get('empresa_id')
            or request.headers.get('Empresa_id')
        )

    def _filial_id(self, request):
        return (
            request.query_params.get('prod_fili')
            or request.query_params.get('filial')
            or request.headers.get('X-Filial')
            or request.session.get('filial_id')
            or request.headers.get('Filial_id')
            or 1
        )

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        
        empresa_id = self._empresa_id(self.request)
        filial_id = self._filial_id(self.request)
        
        # Reutiliza a consulta otimizada, mas sem limite padrão do ListView
        
        return listar_produtos(
            banco=banco,
            empresa_id=empresa_id,
            filial_id=filial_id
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def _status_vencimento(self, lote_data_vali):
        if not lote_data_vali:
            return None
        try:
            hoje = timezone.localdate()
        except Exception:
            hoje = timezone.now().date()
        if lote_data_vali < hoje:
            return 'VENCIDO'
        try:
            delta = (lote_data_vali - hoje).days
        except Exception:
            return 'VÁLIDO'
        if 0 <= delta <= 30:
            return 'PRÓXIMO_VENCIMENTO'
        return 'VÁLIDO'

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            raise NotFound("Banco não encontrado.")

        codigo = self.kwargs.get('codigo') or self.kwargs.get('pk')
        if codigo is None or str(codigo).strip() == '':
            raise NotFound("Código do produto não informado.")

        empresa_id = self.kwargs.get('empresa') or self._empresa_id(self.request)

        qs = Produtos.objects.using(banco).filter(prod_codi=str(codigo))
        if empresa_id is not None and str(empresa_id).strip() != '':
            qs = qs.filter(prod_empr=str(empresa_id))

        obj = qs.order_by('prod_empr').first()
        if not obj:
            raise NotFound("Produto não encontrado.")

        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = dict(serializer.data)

        banco = get_licenca_db_config(request)
        if banco:
            try:
                lote_empr = int(instance.prod_empr)
            except Exception:
                lote_empr = instance.prod_empr

            try:
                lotes_qs = (
                    Lote.objects.using(banco)
                    .filter(lote_empr=lote_empr, lote_prod=str(instance.prod_codi))
                    .order_by('lote_data_fabr', 'lote_lote')
                )
                data['lotes'] = list(
                    lotes_qs.values(
                        'lote_lote',
                        'lote_unit',
                        'lote_sald',
                        'lote_data_fabr',
                        'lote_data_vali',
                        'lote_ativ',
                        'lote_obse',
                    )
                )
            except Exception:
                data['lotes'] = []

            try:
                lotes_total = (
                    Lote.objects.using(banco)
                    .filter(lote_empr=lote_empr, lote_prod=str(instance.prod_codi), lote_ativ=True)
                    .aggregate(total=Sum('lote_sald'))
                    .get('total')
                )
                saldo_lotes = Decimal(str(lotes_total or 0))

                filial_id = self._filial_id(request)
                sp = (
                    SaldoProduto.objects.using(banco)
                    .filter(produto_codigo=instance, empresa=str(instance.prod_empr), filial=str(filial_id))
                    .first()
                )
                saldo_total = Decimal(str(getattr(sp, 'saldo_estoque', 0) or 0))
                saldo_sem_lote = saldo_total - saldo_lotes

                data['saldo_total'] = saldo_total
                data['saldo_lotes'] = saldo_lotes
                data['saldo_sem_lote'] = saldo_sem_lote
            except Exception:
                data['saldo_total'] = None
                data['saldo_lotes'] = None
                data['saldo_sem_lote'] = None

        return Response(data)

    @action(detail=False, methods=['get'])
    def busca(self, request, slug=None):
        banco = get_licenca_db_config(request)
        empresa_id = (
            request.query_params.get('empresa') or 
            request.headers.get('X-Empresa') or 
            request.session.get('empresa_id') or
            request.headers.get('Empresa_id')
        )

        termo = request.query_params.get('q') or request.query_params.get('termo')
        hash_busca = request.query_params.get('hash')
        logger.info(f"Busca produto com filtro: q={termo}, hash={hash_busca}, empresa={empresa_id}")

        # 1. Busca por Hash (QR Code)
        if hash_busca:
            cod_produto = buscar_produto_por_hash(banco, hash_busca, empresa_id)
            if cod_produto:
                produto = buscar_produto_por_codigo(banco, empresa_id, cod_produto)
                if produto:
                    serializer = self.get_serializer(produto)
                    return Response(serializer.data)
            return Response({"detail": "Produto não encontrado via hash"}, status=status.HTTP_404_NOT_FOUND)

        # 2. Busca convencional
        
        # Lógica de fallback para leitura de QR Code direto no campo de busca
        if termo and "/p/" in termo:
            try:
                # Extrai o hash da URL (ex: https://mobile-sps.site/p/HASH)
                parts = termo.split("/p/")
                if len(parts) > 1:
                    hash_extraido = parts[1].strip().split("/")[0].split("?")[0].split("#")[0]
                    
                    cod_produto = buscar_produto_por_hash(banco, hash_extraido, empresa_id)
                    if cod_produto:
                        termo = cod_produto
            except Exception:
                pass

        if not termo:
            return Response([])

        queryset = listar_produtos(
            banco=banco,
            empresa_id=empresa_id,
            q=termo,
            limit=100
        )
        
        serializer = self.get_serializer(queryset, many=True)
        data = list(serializer.data)

        if banco and data:
            try:
                codigos = []
                emprs = set()
                for item in data:
                    codi = (item.get('prod_codi') or '').strip()
                    empr = item.get('prod_empr')
                    if codi:
                        codigos.append(codi)
                    if empr is not None and str(empr).strip() != '':
                        try:
                            emprs.add(int(empr))
                        except Exception:
                            pass

                lotes_rows = []
                if codigos and emprs:
                    lotes_rows = list(
                        Lote.objects.using(banco)
                        .filter(lote_empr__in=list(emprs), lote_prod__in=codigos, lote_ativ=True)
                        .order_by('lote_empr', 'lote_prod', 'lote_data_fabr', 'lote_lote')
                        .values(
                            'lote_empr',
                            'lote_prod',
                            'lote_lote',
                            'lote_unit',
                            'lote_sald',
                            'lote_data_fabr',
                            'lote_data_vali',
                            'lote_ativ',
                            'lote_obse',
                        )[:3000]
                    )

                por_produto = {}
                limite_por_produto = 20
                for r in lotes_rows:
                    chave = (str(r.get('lote_empr')), str(r.get('lote_prod')))
                    arr = por_produto.get(chave)
                    if arr is None:
                        arr = []
                        por_produto[chave] = arr
                    if len(arr) >= limite_por_produto:
                        continue
                    data_vali = r.get('lote_data_vali')
                    data_fabr = r.get('lote_data_fabr')
                    arr.append(
                        {
                            'lote_lote': r.get('lote_lote'),
                            'lote_unit': float(r.get('lote_unit') or 0),
                            'lote_sald': float(r.get('lote_sald') or 0),
                            'lote_data_fabr': data_fabr.isoformat() if hasattr(data_fabr, 'isoformat') else data_fabr,
                            'lote_data_vali': data_vali.isoformat() if hasattr(data_vali, 'isoformat') else data_vali,
                            'lote_ativ': bool(r.get('lote_ativ')),
                            'lote_obse': r.get('lote_obse'),
                            'status_vencimento': self._status_vencimento(data_vali),
                        }
                    )

                for item in data:
                    chave = (str(item.get('prod_empr')), str(item.get('prod_codi')))
                    item['lotes'] = por_produto.get(chave, [])
            except Exception:
                for item in data:
                    item['lotes'] = []

        return Response(data)

    @action(detail=False, methods=['post'])
    def impressao_etiquetas(self, request):
        banco = get_licenca_db_config(request)
        empresa_id = request.data.get('empresa_id')
        produtos_ids = request.data.get('produtos', [])

        if not empresa_id or not produtos_ids:
            return Response(
                {"error": "Empresa e lista de produtos são obrigatórios"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        etiquetas = gerar_dados_etiquetas(banco, empresa_id, produtos_ids)
        return Response(etiquetas)

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
        
        # Preparar dados
        dados_preco = request.data.copy()
        
        try:
            preco_existente = Tabelaprecos.objects.using(banco).get(
                tabe_prod=produto.prod_codi,
                tabe_empr=produto.prod_empr,
                tabe_fili=dados_preco.get('tabe_fili', 1)
            )
            
            # Remover campos que não devem ser atualizados diretamente se não fornecidos
            campos_validos = [f.name for f in Tabelaprecos._meta.fields]
            dados_limpos = {k: v for k, v in dados_preco.items() if k in campos_validos}
            
            atualizar_preco_com_historico(banco, preco_existente, dados_limpos)
            serializer = TabelaPrecoSerializer(preco_existente, context={'banco': banco})
            return Response(serializer.data)
            
        except Tabelaprecos.DoesNotExist:
            dados_preco['tabe_prod'] = produto.prod_codi
            dados_preco['tabe_empr'] = produto.prod_empr
            dados_preco['tabe_fili'] = dados_preco.get('tabe_fili', 1)
            
            # Remover campos inválidos
            campos_validos = [f.name for f in Tabelaprecos._meta.fields]
            dados_limpos = {k: v for k, v in dados_preco.items() if k in campos_validos}
            
            novo_preco = criar_preco_com_historico(banco, dados_limpos)
            serializer = TabelaPrecoSerializer(novo_preco, context={'banco': banco})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def precos_promocionais(self, request, pk=None):
        produto = self.get_object()
        banco = get_licenca_db_config(request)

        precos = TabelaprecosPromocional.objects.using(banco).filter(
            tabe_prod=produto.prod_codi,
            tabe_empr=produto.prod_empr,
        )
        serializer = TabelaPrecoPromocionalSerializer(precos, many=True, context={'banco': banco})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def precos_promocionais_historico(self, request, pk=None):
        produto = self.get_object()
        banco = get_licenca_db_config(request)

        hist = (
            TabelaprecosPromocionalhist.objects.using(banco)
            .filter(tabe_prod=produto.prod_codi, tabe_empr=produto.prod_empr)
            .order_by('-tabe_data_hora')[:200]
        )
        serializer = TabelaPrecoPromocionalHistSerializer(hist, many=True, context={'banco': banco})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def atualizar_precos_promocionais(self, request, pk=None):
        produto = self.get_object()
        banco = get_licenca_db_config(request)

        dados_preco = request.data.copy()
        tabe_fili = dados_preco.get('tabe_fili', 1)

        try:
            preco_existente = TabelaprecosPromocional.objects.using(banco).get(
                tabe_prod=produto.prod_codi,
                tabe_empr=produto.prod_empr,
                tabe_fili=tabe_fili,
            )

            campos_validos = [f.name for f in TabelaprecosPromocional._meta.fields]
            dados_limpos = {k: v for k, v in dados_preco.items() if k in campos_validos}

            atualizar_preco_promocional_com_historico(banco, preco_existente, dados_limpos)
            serializer = TabelaPrecoPromocionalSerializer(preco_existente, context={'banco': banco})
            return Response(serializer.data)

        except TabelaprecosPromocional.DoesNotExist:
            dados_preco['tabe_prod'] = produto.prod_codi
            dados_preco['tabe_empr'] = produto.prod_empr
            dados_preco['tabe_fili'] = tabe_fili

            campos_validos = [f.name for f in TabelaprecosPromocional._meta.fields]
            dados_limpos = {k: v for k, v in dados_preco.items() if k in campos_validos}

            novo_preco = criar_preco_promocional_com_historico(banco, dados_limpos)
            serializer = TabelaPrecoPromocionalSerializer(novo_preco, context={'banco': banco})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def cadastro_servico(self, request):
        """
        Endpoint específico para cadastro simplificado de serviços/produtos.
        """
        banco = get_licenca_db_config(request)
        serializer = ProdutoServicoSerializer(data=request.data, context={'banco': banco})
        
        if serializer.is_valid():
            produto = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def cadastro_rapido(self, request, slug=None):
        """
        Cadastro rápido de produto com campos essenciais, gerando código sequencial por empresa.
        Campos aceitos:
          - prod_nome (obrigatório)
          - unme (obrigatório) código da unidade (unid_codi)
          - ncm (obrigatório) código do NCM
          - preco_vista / preco_prazo (opcionais) para criar/atualizar Tabela de Preços
        """
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"detail": "Banco não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        empresa_id = (
            request.headers.get('X-Empresa') or
            request.session.get('empresa_id')
        )
        filial_id = (
            request.headers.get('X-Filial') or
            request.session.get('filial_id')
        )
        if not empresa_id:
            return Response({"detail": "Empresa não informada."}, status=status.HTTP_400_BAD_REQUEST)

        nome = (request.data.get('prod_nome') or request.data.get('nome') or '').strip()
        if not nome:
            return Response({"detail": "prod_nome é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        unme_code_or_id = (request.data.get('unme') or request.data.get('prod_unme') or '').strip()
        if not unme_code_or_id:
            return Response({"detail": "unme é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        ncm_code = (request.data.get('ncm') or request.data.get('prod_ncm') or '').strip()
        if not ncm_code:
            return Response({"detail": "ncm é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        unidade = None
        master_alias = get_ncm_master_db(banco)
        unme_code = str(unme_code_or_id).upper()
        master_unme = UnidadeMedida.objects.using(master_alias).filter(unid_codi=unme_code).first()
        if not master_unme:
            return Response({"detail": "Unidade de medida inválida."}, status=status.HTTP_400_BAD_REQUEST)
        unidade = UnidadeMedida.objects.using(banco).filter(unid_codi=unme_code).first()
        if not unidade:
            unidade = UnidadeMedida(unid_codi=unme_code, unid_desc=getattr(master_unme, 'unid_desc', unme_code))
            unidade.save(using=banco)

        digits = ''.join(ch for ch in str(ncm_code) if ch.isdigit())
        candidates = []
        for c in (str(ncm_code).strip(), digits):
            if c and c not in candidates:
                candidates.append(c)
        if digits and len(digits) == 8:
            dotted = f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
            if dotted not in candidates:
                candidates.insert(1, dotted)
        ncm_obj = None
        for code in candidates:
            ncm_obj = Ncm.objects.using(master_alias).filter(ncm_codi=code).first()
            if ncm_obj:
                break
        if not ncm_obj:
            return Response({"detail": "NCM inválido."}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            'prod_empr': str(empresa_id),
            'prod_fili': str(filial_id) if filial_id else None,
            'prod_nome': nome,
            'prod_ncm': ncm_obj.ncm_codi,
        }
        if unidade:
            payload['prod_unme'] = unidade.pk

        preco_vista = request.data.get('preco_vista')
        preco_prazo = request.data.get('preco_prazo')

        serializer = ProdutoSerializer(data=payload, context={'banco': banco})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        produto = serializer.save()

        if preco_vista is not None or preco_prazo is not None:
            tabe_fili = str(filial_id) if filial_id else '1'
            preco_ctx = {
                'using': banco,
                'tabe_empr': produto.prod_empr,  
                'tabe_fili': tabe_fili,
                'tabe_prod': produto.prod_codi,
            }
            preco_data = {}
            if preco_vista is not None and str(preco_vista).strip() != '':
                preco_data['tabe_avis'] = str(preco_vista)
            if preco_prazo is not None and str(preco_prazo).strip() != '':
                preco_data['tabe_apra'] = str(preco_prazo)
            if preco_data:
                t_serializer = TabelaPrecoSerializer(data=preco_data, context=preco_ctx)
                if t_serializer.is_valid():
                    try:
                        t_serializer.save()
                    except Exception as e:
                        logger.warning(f"Falha ao gravar preços do cadastro rápido: {e}")
                else:
                    logger.warning(f"Falha ao gravar preços do cadastro rápido: {t_serializer.errors}")

        return Response(ProdutoSerializer(produto, context={'banco': banco}).data, status=status.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        precos_data = request.data.pop('precos', None)
        
        serializer = self.get_serializer(
            data=request.data, 
            context={'banco': banco}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Se houver dados de preço, criar
        if precos_data and serializer.instance:
            precos_data['tabe_prod'] = serializer.instance.prod_codi
            precos_data['tabe_empr'] = serializer.instance.prod_empr
            precos_data['tabe_fili'] = 1 # Padrão
            criar_preco_com_historico(banco, precos_data)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request)
        instance = self.get_object()
        precos_data = request.data.pop('precos', None)

        # Atualizar produto
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.pop('partial', False),
            context={'banco': banco}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Atualizar preço se fornecido
        if precos_data:
            try:
                preco = Tabelaprecos.objects.using(banco).get(
                    tabe_prod=instance.prod_codi,
                    tabe_empr=instance.prod_empr,
                    tabe_fili=1
                )
                atualizar_preco_com_historico(banco, preco, precos_data)
            except Tabelaprecos.DoesNotExist:
                precos_data['tabe_prod'] = instance.prod_codi
                precos_data['tabe_empr'] = instance.prod_empr
                precos_data['tabe_fili'] = 1
                criar_preco_com_historico(banco, precos_data)

        return Response(serializer.data)
