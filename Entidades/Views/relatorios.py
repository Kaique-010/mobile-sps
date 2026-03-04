

from re import T
from django.db.models import Q
from Pedidos.models import PedidoVenda, PedidosGeral,Itenspedidovenda
from Orcamentos.models import Orcamentos,ItensOrcamento
from O_S.models import  Os
from rest_framework.decorators import action
from rest_framework.response import Response
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # DEBUG: Verificar tamanho do queryset
        count = queryset.count()
        print(f"DEBUG: OrdemServicoViewSet.list - Total de registros encontrados: {count}")

        page = self.paginate_queryset(queryset)
        if page is not None:
            print(f"DEBUG: Paginando {len(page)} registros.")
            self._prefetch_related_objects(page)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        print("DEBUG: Sem paginação, retornando tudo (CUIDADO).")
        self._prefetch_related_objects(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
        
        # Filtros
        status_param = self.request.query_params.get('status')
        data_inicial = self.request.query_params.get('data_inicial')
        data_final = self.request.query_params.get('data_final')

        if status_param:
            queryset = queryset.filter(orde_stat_orde=status_param)
        
        if data_inicial:
            queryset = queryset.filter(orde_data_aber__gte=data_inicial)
        
        if data_final:
            queryset = queryset.filter(orde_data_aber__lte=data_final)

        # BLINDAGEM CONTRA DATAS CORROMPIDAS (ex: ano -18)
        # Deferir campos de data que podem quebrar o driver psycopg2
        date_fields = [
            'orde_data_aber', 'orde_data_fech', 
            'orde_nf_data', 'orde_data_repr', 'orde_ulti_alte'
        ]
        queryset = queryset.defer(*date_fields)
        
        # Injetar campos seguros como texto
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        
        # Tenta recuperar permissões já injetadas no request
        if getattr(self.request, 'permissoes', None):
            context['permissoes'] = self.request.permissoes
            return context

        # Se não tiver, tenta extrair novamente do header (fallback)
        session_id = self.request.headers.get('X-Session-ID')
        if session_id:
            try:
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
                        
                        # Injeta no contexto E no request para garantir
                        context['permissoes'] = permissoes
                        self.request.permissoes = permissoes
            except Exception as e:
                print(f"Erro ao injetar permissões no get_serializer_context: {e}")
        
        return context

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        
        # Garantir que permissões estejam carregadas
        if not getattr(request, 'permissoes', None):
            session_id = request.headers.get('X-Session-ID')
            if session_id:
                try:
                    parts = session_id.split('_')
                    if len(parts) >= 3:
                        cliente_id = parts[0]
                        usuario_tipo = parts[-1]
                        # Reconstrói banco slug caso contenha underscores
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
                            
                            # Garantir outros atributos de contexto se necessário
                            if not getattr(request, 'banco', None):
                                request.banco = banco_slug
                            if not getattr(request, 'cliente_id', None):
                                request.cliente_id = cliente_id
                                
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
            queryset = self.get_queryset().filter(orde_stat_orde=22)
            print("ordens em estoque:", queryset)
            # USAR self.get_serializer para injetar o contexto (request, banco, permissoes)
            serializer = self.get_serializer(queryset, many=True)
            return tratar_sucesso(serializer.data)
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