

from re import T
from django.core.cache import cache
from django.db.models import Q
from Pedidos.models import PedidoVenda, PedidosGeral,Itenspedidovenda
import logging
from Orcamentos.models import Orcamentos,ItensOrcamento
from O_S.models import  Os
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import status
from Entidades.models import Entidades
from Produtos.models import Produtos
from OrdemdeServico.models import (
    Ordemservico,
    Ordemservicoimgantes,
    Ordemservicoimgdurante,
    Ordemservicoimgdepois,
    Ordemservicopecas,
    Ordemservicoservicos,
    OrdemServicoFaseSetor,
    WorkflowSetor
)
from Pedidos.rest.serializers import PedidoVendaSerializer, PedidosGeralSerializer, ItemPedidoVendaSerializer
from Orcamentos.rest.serializers import OrcamentosSerializer, ItemOrcamentoSerializer
from O_S.REST.serializers import OrdemServicoGeralSerializer, OsSerializer
from OrdemdeServico.serializers import (
    OrdemServicoSerializer,
    ImagemAntesSerializer,
    ImagemDuranteSerializer,
    ImagemDepoisSerializer
)
from .base_cliente import BaseClienteViewSet
from core.excecoes import ErroDominio
from core.dominio_handler import tratar_erro, tratar_sucesso
from django.core.cache import cache


class PedidosViewSet(BaseClienteViewSet):
    queryset = PedidoVenda.objects.all()
    serializer_class = PedidoVendaSerializer

class PedidosGeralViewSet(BaseClienteViewSet):
    queryset = PedidosGeral.objects.all()
    serializer_class = PedidosGeralSerializer

class ItensPedidosVendaViewSet(BaseClienteViewSet):
    queryset = Itenspedidovenda.objects.all()
    serializer_class = ItemPedidoVendaSerializer

class ItensOrcamentoViewSet(BaseClienteViewSet):
    queryset = ItensOrcamento.objects.all()
    serializer_class = ItemOrcamentoSerializer


class OrcamentosViewSet(BaseClienteViewSet):
    queryset = Orcamentos.objects.all()
    serializer_class = OrcamentosSerializer

from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class OrdemServicoViewSet(BaseClienteViewSet):
    queryset = Ordemservico.objects.all()
    pagination_class = StandardResultsSetPagination
    
    serializer_class = OrdemServicoSerializer
    logger = logging.getLogger(__name__)

    def _cache_key(self, base: str, status_override=None):
        banco = getattr(self.request, 'banco', None) or 'default'
        cliente = getattr(self.request, 'cliente_id', '')
        permissoes = getattr(self.request, 'permissoes', {}) or {}
        ver_preco = 1 if permissoes.get('ver_preco', True) else 0
        ver_foto = 1 if permissoes.get('ver_foto', True) else 0
        qp = self.request.query_params
        status_value = status_override if status_override is not None else qp.get('status', '')
        numero_value = qp.get('orde_nume') or qp.get('numero') or qp.get('ordem') or ''
        motor_value = qp.get('motor', '')
        tipo_value = qp.get('tipo') or qp.get('orde_tipo') or ''
        voltagem_value = qp.get('voltagem') or qp.get('orde_volt') or ''
        potencia_value = qp.get('potencia') or qp.get('orde_pote') or ''
        parts = [
            f"b={banco}",
            f"c={cliente}",
            f"vp={ver_preco}",
            f"vf={ver_foto}",
            f"s={status_value}",
            f"di={qp.get('data_inicial','')}",
            f"df={qp.get('data_final','')}",
            f"n={numero_value}",
            f"m={motor_value}",
            f"t={tipo_value}",
            f"v={voltagem_value}",
            f"po={potencia_value}",
            f"p={qp.get('page','')}",
            f"ps={qp.get('page_size','')}",
        ]
        return f"os:{base}:" + "|".join(parts)
    
    def _should_refresh(self):
        val = (self.request.query_params.get('refresh') or '').strip().lower()
        return val in ('1', 'true', 'yes', 'y')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        cache_key = self._cache_key('lista')
        if not self._should_refresh():
            cached = cache.get(cache_key)
            if cached is not None:
                try:
                    self.logger.info(f"[CACHE HIT][OS list] key={cache_key} size={len(cached) if isinstance(cached, list) else 'page'}")
                except Exception:
                    pass
                return Response(cached)

        page = self.paginate_queryset(queryset)
        if page is not None:
            self._prefetch_related_objects(page)
            serializer = self.get_serializer(page, many=True)
            resp = self.get_paginated_response(serializer.data)
            cache.set(cache_key, resp.data)
            try:
                self.logger.info(f"[CACHE SET][OS list] key={cache_key} paginated=1")
            except Exception:
                pass
            return Response(resp.data)

        self._prefetch_related_objects(queryset)
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        cache.set(cache_key, data)
        try:
            self.logger.info(f"[CACHE SET][OS list] key={cache_key} paginated=0 size={len(data)}")
        except Exception:
            pass
        return Response(data)

    def _aplicar_filtros(self, queryset, incluir_status=True):
        qp = self.request.query_params

        status_param = (qp.get('status') or '').strip()
        data_inicial = (qp.get('data_inicial') or '').strip()
        data_final = (qp.get('data_final') or '').strip()

        numero_ordem = (qp.get('orde_nume') or qp.get('numero') or qp.get('ordem') or '').strip()
        motor = (qp.get('motor') or '').strip()
        tipo = (qp.get('tipo') or qp.get('orde_tipo') or '').strip()
        voltagem = (qp.get('voltagem') or qp.get('orde_volt') or '').strip()
        potencia = (qp.get('potencia') or qp.get('orde_pote') or '').strip()

        if incluir_status and status_param:
            queryset = queryset.filter(orde_stat_orde=status_param)

        if data_inicial:
            queryset = queryset.filter(orde_data_aber__gte=data_inicial)

        if data_final:
            queryset = queryset.filter(orde_data_aber__lte=data_final)

        if numero_ordem:
            try:
                queryset = queryset.filter(orde_nume=int(numero_ordem))
            except (TypeError, ValueError):
                pass

        if motor:
            queryset = queryset.filter(
                Q(orde_mode__icontains=motor)
                | Q(orde_seri__icontains=motor)
                | Q(orde_patr__icontains=motor)
                | Q(orde_plac__icontains=motor)
            )

        if tipo:
            queryset = queryset.filter(orde_tipo=tipo)

        if voltagem:
            try:
                queryset = queryset.filter(orde_volt=int(voltagem))
            except (TypeError, ValueError):
                pass

        if potencia:
            queryset = queryset.filter(orde_pote__icontains=potencia)

        return queryset

    def _blindar_datas(self, queryset):
        date_fields = [
            'orde_data_aber', 'orde_data_fech',
            'orde_nf_data', 'orde_data_repr', 'orde_ulti_alte'
        ]
        queryset = queryset.defer(*date_fields)

        select_dict = {}
        for field in date_fields:
            select_dict[f'safe_{field}'] = f"""
                CASE 
                    WHEN {field} IS NOT NULL 
                         AND EXTRACT(YEAR FROM {field}) BETWEEN 2020 AND 2100 
                    THEN {field}::text 
                    ELSE NULL 
                END
            """
        queryset = queryset.extra(select=select_dict)
        return queryset

    def _prefetch_related_objects(self, objects):
        if not objects:
            return
            
        banco = self.request.banco
        
        # Coletar IDs das ordens
        orde_ids = [obj.orde_nume for obj in objects]
        
        # 1. Prefetch Peças
        try:
            pecas = Ordemservicopecas.objects.using(banco).filter(peca_orde__in=orde_ids)
            pecas_map = {}
            for peca in pecas:
                if peca.peca_orde not in pecas_map:
                    pecas_map[peca.peca_orde] = []
                pecas_map[peca.peca_orde].append(peca)
        except Exception:
            pecas_map = {}
            
        # 2. Prefetch Serviços
        try:
            servicos = Ordemservicoservicos.objects.using(banco).filter(serv_orde__in=orde_ids)
            servicos_map = {}
            for serv in servicos:
                if serv.serv_orde not in servicos_map:
                    servicos_map[serv.serv_orde] = []
                servicos_map[serv.serv_orde].append(serv)
        except Exception:
            servicos_map = {}
            
        # 2.1 Prefetch Nomes de Produtos e Serviços (para evitar queries nos serializers de itens)
        try:
            # Coletar códigos de produtos (peças) e serviços
            codigos_produtos = set()
            
            # De peças
            all_pecas = [p for sublist in pecas_map.values() for p in sublist]
            for p in all_pecas:
                if p.peca_codi:
                    codigos_produtos.add(str(p.peca_codi))
            
            # De serviços
            all_servicos = [s for sublist in servicos_map.values() for s in sublist]
            for s in all_servicos:
                if s.serv_codi:
                    codigos_produtos.add(str(s.serv_codi))
            
            produtos_map = {}
            if codigos_produtos:
                # Buscar produtos em lote
                # Nota: Produtos.prod_codi é CharField, e prod_codi_nume também pode ser usado
                prods = Produtos.objects.using(banco).filter(
                    Q(prod_codi__in=codigos_produtos) | Q(prod_codi_nume__in=codigos_produtos)
                )
                
                # Mapear por código para acesso rápido
                for prod in prods:
                    # Mapeia tanto pelo código string quanto pelo numérico se existir
                    if prod.prod_codi:
                        produtos_map[str(prod.prod_codi)] = prod.prod_nome
                    if prod.prod_codi_nume:
                        produtos_map[str(prod.prod_codi_nume)] = prod.prod_nome
            
            # Atribuir nomes aos objetos de peças
            for p in all_pecas:
                nome = produtos_map.get(str(p.peca_codi), "")
                p._prefetched_produto_nome = nome
                
            # Atribuir nomes aos objetos de serviços
            for s in all_servicos:
                nome = produtos_map.get(str(s.serv_codi), "")
                s._prefetched_servico_nome = nome
                
        except Exception as e:
            # Em caso de erro, segue sem nomes pré-carregados (o serializer fará a query individualmente)
            pass

        # 3. Prefetch Setores (Nomes)
        try:
            setor_ids = set(obj.orde_seto for obj in objects if obj.orde_seto)
            setores_nomes = {}
            if setor_ids:
                setores_qs = OrdemServicoFaseSetor.objects.using(banco).filter(osfs_codi__in=setor_ids)
                setores_nomes = {s.osfs_codi: s.osfs_nome for s in setores_qs}
        except Exception:
            setores_nomes = {}

        # 4. Prefetch Próximos Setores (Workflow)
        try:
            # Coletar IDs de origem (setor atual da OS)
            # Se orde_seto for None/0, considera origem 0
            origem_ids = set()
            for obj in objects:
                origem = obj.orde_seto if obj.orde_seto else 0
                origem_ids.add(origem)
            
            workflow_map = {}
            if origem_ids:
                workflows = WorkflowSetor.objects.using(banco).filter(
                    wkfl_seto_orig__in=origem_ids,
                    wkfl_ativo=True
                ).order_by('wkfl_orde')
                
                for wf in workflows:
                    if wf.wkfl_seto_orig not in workflow_map:
                        workflow_map[wf.wkfl_seto_orig] = []
                    workflow_map[wf.wkfl_seto_orig].append(wf)
        except Exception:
            workflow_map = {}

        # 5. Prefetch Cliente (nome)
        # Como é endpoint do cliente, todos pertencem ao mesmo cliente logado
        cliente_nome = None
        try:
             # Tenta pegar da sessão/permissão se já tiver
             entidade = Entidades.objects.using(banco).filter(enti_clie=self.request.cliente_id).first()
             cliente_nome = entidade.enti_nome if entidade else None
        except:
             pass

        # Atribuir aos objetos para o Serializer usar
        for obj in objects:
            obj._prefetched_pecas = pecas_map.get(obj.orde_nume, [])
            obj._prefetched_servicos = servicos_map.get(obj.orde_nume, [])
            
            if obj.orde_seto in setores_nomes:
                obj._prefetched_setor_nome = setores_nomes[obj.orde_seto]
            
            # Próximos setores
            origem = obj.orde_seto if obj.orde_seto else 0
            obj._prefetched_proximos_setores = workflow_map.get(origem, [])
            
            if cliente_nome:
                obj._prefetched_cliente_nome = cliente_nome

    def get_queryset(self):
        queryset = super().get_queryset()
        
        queryset = self._aplicar_filtros(queryset, incluir_status=True)
        queryset = self._blindar_datas(queryset)
        # Ordenação determinística para evitar UnorderedObjectListWarning na paginação
        queryset = queryset.order_by('-orde_nume')
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        
        if getattr(self.request, 'permissoes', None):
            context['permissoes'] = self.request.permissoes
            return context

        session_id = self.request.headers.get('X-Session-ID')
        if session_id:
            try:
                from django.core.cache import cache as _cache
                session_key = f"session:{session_id}:permissoes"
                cached = _cache.get(session_key)
                if cached:
                    context['permissoes'] = cached
                    self.request.permissoes = cached
                    try:
                        logging.getLogger(__name__).info(f"[CACHE HIT][SESSION] key={session_key}")
                    except Exception:
                        pass
                    return context
                parts = session_id.split('_')
                if len(parts) >= 3:
                    cliente_id = parts[0]
                    usuario_tipo = parts[-1]
                    banco_slug = "_".join(parts[1:-1])
                    
                    entidade = Entidades.objects.using(banco_slug).filter(enti_clie=cliente_id).first()
                    if entidade:
                        permissoes = {}
                        if usuario_tipo == 'usuario1':
                            permissoes['ver_preco'] = entidade.enti_mobi_prec
                            permissoes['ver_foto'] = entidade.enti_mobi_foto
                        elif usuario_tipo == 'usuario2':
                            permissoes['ver_preco'] = entidade.enti_usua_prec
                            permissoes['ver_foto'] = entidade.enti_usua_foto
                        
                        context['permissoes'] = permissoes
                        self.request.permissoes = permissoes
                        _cache.set(session_key, permissoes)
                        try:
                            logging.getLogger(__name__).info(f"[CACHE SET][SESSION] key={session_key}")
                        except Exception:
                            pass
            except Exception as e:
                print(f"Erro ao injetar permissões no get_serializer_context: {e}")
        
        return context

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        
        if not getattr(request, 'permissoes', None):
            session_id = request.headers.get('X-Session-ID')
            if session_id:
                try:
                    from django.core.cache import cache as _cache
                    session_key = f"session:{session_id}:permissoes"
                    cached = _cache.get(session_key)
                    if cached:
                        request.permissoes = cached
                        try:
                            logging.getLogger(__name__).info(f"[CACHE HIT][SESSION] key={session_key}")
                        except Exception:
                            pass
                        return
                    parts = session_id.split('_')
                    if len(parts) >= 3:
                        cliente_id = parts[0]
                        usuario_tipo = parts[-1]
                        banco_slug = "_".join(parts[1:-1])
                        
                        entidade = Entidades.objects.using(banco_slug).filter(enti_clie=cliente_id).first()
                        if entidade:
                            permissoes = {}
                            if usuario_tipo == 'usuario1':
                                permissoes['ver_preco'] = entidade.enti_mobi_prec
                                permissoes['ver_foto'] = entidade.enti_mobi_foto
                            elif usuario_tipo == 'usuario2':
                                permissoes['ver_preco'] = entidade.enti_usua_prec
                                permissoes['ver_foto'] = entidade.enti_usua_foto
                            
                            request.permissoes = permissoes
                            
                            if not getattr(request, 'banco', None):
                                request.banco = banco_slug
                            if not getattr(request, 'cliente_id', None):
                                request.cliente_id = cliente_id
                            _cache.set(session_key, permissoes)
                            try:
                                logging.getLogger(__name__).info(f"[CACHE SET][SESSION] key={session_key}")
                            except Exception:
                                pass
                                
                except Exception as e:
                    print(f"Erro ao injetar permissões no initial: {e}")
    @action(detail=False, methods=['post'], url_path='definir-permissao-preco')
    def definir_permissao_preco(self, request):
        try:
            permitir = request.data.get('permitir')
            usuario_tipo = request.data.get('usuario') # 'mobi' ou 'usua'

            if permitir is None:
                return Response({'erro': 'Parâmetro permitir é obrigatório'}, status=400)
            
            # Converter para boolean corretamente
            if isinstance(permitir, str):
                permitir = permitir.lower() == 'true'
            else:
                permitir = bool(permitir)
            
            # Atualizar entidade
            from Entidades.models import Entidades
            entidade = Entidades.objects.using(request.banco).filter(enti_clie=request.cliente_id).first()
            if not entidade:
                return Response({'erro': 'Cliente não encontrado'}, status=404)
            
            # Atualizar baseado no tipo de usuário ou ambos
            if usuario_tipo == 'mobi':
                entidade.enti_mobi_prec = permitir
            elif usuario_tipo == 'usua':
                entidade.enti_usua_prec = permitir
            else:
                entidade.enti_mobi_prec = permitir
                entidade.enti_usua_prec = permitir
                
            entidade.save(using=request.banco)
            
            return tratar_sucesso({'ver_preco': permitir, 'usuario': usuario_tipo})
        except Exception as e:
            return tratar_erro(e)

    @action(detail=False, methods=['post'], url_path='definir-permissao-foto')
    def definir_permissao_foto(self, request):
        try:
            permitir = request.data.get('permitir')
            usuario_tipo = request.data.get('usuario') # 'mobi' ou 'usua'

            if permitir is None:
                return Response({'erro': 'Parâmetro permitir é obrigatório'}, status=400)
            
            if isinstance(permitir, str):
                permitir = permitir.lower() == 'true'
            else:
                permitir = bool(permitir)
            
            # Atualizar entidade
            from Entidades.models import Entidades
            entidade = Entidades.objects.using(request.banco).filter(enti_clie=request.cliente_id).first()
            if not entidade:
                return Response({'erro': 'Cliente não encontrado'}, status=404)
            
            # Atualizar baseado no tipo de usuário ou ambos
            if usuario_tipo == 'mobi':
                entidade.enti_mobi_foto = permitir
            elif usuario_tipo == 'usua':
                entidade.enti_usua_foto = permitir
            else:
                entidade.enti_mobi_foto = permitir
                entidade.enti_usua_foto = permitir

            entidade.save(using=request.banco)
            
            return tratar_sucesso({'ver_foto': permitir, 'usuario': usuario_tipo})
        except Exception as e:
            return tratar_erro(e)

    @action(detail=False, methods=['get'], url_path='em-estoque')
    def listar_ordem_em_estoque(self, request, *args, **kwargs):
        try:
            cache_key = self._cache_key('estoque', status_override='22')
            if not self._should_refresh():
                cached = cache.get(cache_key)
                if cached is not None:
                    try:
                        self.logger.info(f"[CACHE HIT][OS estoque] key={cache_key} size={len(cached)}")
                    except Exception:
                        pass
                    return tratar_sucesso(cached)

            queryset = super().get_queryset()
            queryset = self._aplicar_filtros(queryset, incluir_status=False)
            queryset = queryset.filter(orde_stat_orde=22)
            queryset = self._blindar_datas(queryset).order_by('-orde_nume')
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            cache.set(cache_key, data)
            try:
                self.logger.info(f"[CACHE SET][OS estoque] key={cache_key} size={len(data)}")
            except Exception:
                pass
            return tratar_sucesso(data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
    
    
    @action(detail=False, methods=['get'], url_path='imagensantes')
    def listar_imagens_antes(self, request, *args, **kwargs):
        try:
            # Verificar permissão de visualização de foto
            permissoes = getattr(request, 'permissoes', {})
            if not permissoes.get('ver_foto', True):
                 return tratar_sucesso([])

            orde_nume = request.query_params.get('orde_nume')
            if not orde_nume:
                raise ValueError("O parâmetro 'orde_nume' é obrigatório.")
            
            print(f"DEBUG: Buscando imagens ANTES para ordem {orde_nume} no banco {request.banco}")
            
            # Verificar se a ordem pertence ao cliente para obter empresa/filial corretas
            # E garantir segurança
            qs_ordem = Ordemservico.objects.using(request.banco).filter(
                orde_nume=orde_nume,
                orde_enti=request.cliente_id
            )
            
            if not qs_ordem.exists():
                print(f"DEBUG: Ordem {orde_nume} não encontrada para o cliente {request.cliente_id}")
                # Retorna vazio se não for do cliente
                return tratar_sucesso([])
                
            ordem = qs_ordem.first()
            print(f"DEBUG: Ordem encontrada. Empr: {ordem.orde_empr}, Fili: {ordem.orde_fili}")
                
            imagensAntes = Ordemservicoimgantes.objects.using(request.banco).filter(
                iman_orde=orde_nume,
                iman_empr=ordem.orde_empr,
                iman_fili=ordem.orde_fili
            )
            
            print(f"DEBUG: Encontrados {imagensAntes.count()} registros de imagens ANTES")
            
            for img in imagensAntes:
                tamanho = len(img.iman_imag) if img.iman_imag else 0
                print(f"DEBUG: Imagem ID {img.iman_id} tem tamanho {tamanho} bytes")

            context = self.get_serializer_context()
            serializer = ImagemAntesSerializer(imagensAntes, many=True, context=context)
            return tratar_sucesso(serializer.data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
        
        
    @action(detail=False, methods=['get'], url_path='imagensdepois')
    def listar_imagens_depois(self, request, *args, **kwargs):
        try:
            # Verificar permissão de visualização de foto
            permissoes = getattr(request, 'permissoes', {})
            if not permissoes.get('ver_foto', True):
                 return tratar_sucesso([])

            orde_nume = request.query_params.get('orde_nume')
            if not orde_nume:
                raise ValueError("O parâmetro 'orde_nume' é obrigatório.")

            print(f"DEBUG: Buscando imagens DEPOIS para ordem {orde_nume} no banco {request.banco}")
            
            qs_ordem = Ordemservico.objects.using(request.banco).filter(
                orde_nume=orde_nume,
                orde_enti=request.cliente_id
            )
            
            if not qs_ordem.exists():
                print(f"DEBUG: Ordem {orde_nume} não encontrada para o cliente {request.cliente_id}")
                return tratar_sucesso([])
                
            ordem = qs_ordem.first()

            imagensDepois = Ordemservicoimgdepois.objects.using(request.banco).filter(
                imde_orde=orde_nume,
                imde_empr=ordem.orde_empr,
                imde_fili=ordem.orde_fili
            )
            
            print(f"DEBUG: Encontrados {imagensDepois.count()} registros de imagens DEPOIS")

            for img in imagensDepois:
                tamanho = len(img.imde_imag) if img.imde_imag else 0
                print(f"DEBUG: Imagem ID {img.imde_id} tem tamanho {tamanho} bytes")

            context = self.get_serializer_context()
            serializer = ImagemDepoisSerializer(imagensDepois, many=True, context=context)
            return tratar_sucesso(serializer.data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
        
        
    @action(detail=False, methods=['get'], url_path='imagensdurante')
    def listar_imagens_durante(self, request, *args, **kwargs):
        try:
            # Verificar permissão de visualização de foto
            permissoes = getattr(request, 'permissoes', {})
            if not permissoes.get('ver_foto', True):
                 return tratar_sucesso([])

            orde_nume = request.query_params.get('orde_nume')
            if not orde_nume:
                raise ValueError("O parâmetro 'orde_nume' é obrigatório.")

            print(f"DEBUG: Buscando imagens DURANTE para ordem {orde_nume} no banco {request.banco}")
            
            qs_ordem = Ordemservico.objects.using(request.banco).filter(
                orde_nume=orde_nume,
                orde_enti=request.cliente_id
            )
            
            if not qs_ordem.exists():
                print(f"DEBUG: Ordem {orde_nume} não encontrada para o cliente {request.cliente_id}")
                return tratar_sucesso([])
                
            ordem = qs_ordem.first()

            imagensDurante = Ordemservicoimgdurante.objects.using(request.banco).filter(
                imdu_orde=orde_nume,
                imdu_empr=ordem.orde_empr,
                imdu_fili=ordem.orde_fili
            )
            
            print(f"DEBUG: Encontrados {imagensDurante.count()} registros de imagens DURANTE")

            for img in imagensDurante:
                tamanho = len(img.imdu_imag) if img.imdu_imag else 0
                print(f"DEBUG: Imagem ID {img.imdu_id} tem tamanho {tamanho} bytes")

            context = self.get_serializer_context()
            serializer = ImagemDuranteSerializer(imagensDurante, many=True, context=context)
            return tratar_sucesso(serializer.data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
class OsViewSet(BaseClienteViewSet):
    queryset = Os.objects.all()
    serializer_class = OsSerializer
