from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from django.core.exceptions import ValidationError  
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework import status
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.utils import get_db_from_slug
from .models import Entidades
from .serializers import EntidadesSerializer, EntidadesTipoOutrosSerializer
from .utils import buscar_endereco_por_cep
from django.db.models import Q
from django.core.cache import cache
from .services.entidades_tipooutros import EntidadeServico


BANCOS_CEP_FIXO = {"savexml896", "pg pisos", 'demonstracao'}
CEP_FALLBACK_PG_PISOS = "84010200"
CEP_FALLBACK_DEMONSTRACAO = "84015265"

class EntidadesViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modulo_requerido = 'Entidades'
    permission_classes = [IsAuthenticated]
    serializer_class = EntidadesSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['enti_nome', 'enti_nume']
    lookup_field = 'enti_clie'
    filterset_fields = ['enti_empr']

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        print(f"\n🔍 Banco de dados selecionado: {banco}")
        
        if not banco:
            return Entidades.objects.none()
        empresa_id = self.request.query_params.get('enti_empr') or self.request.headers.get("X-Empresa") or self.request.session.get("empresa_id") or self.request.headers.get("Empresa_id")
        # Base queryset otimizada
        queryset = Entidades.objects.using(banco).filter(enti_empr= empresa_id)
        # Aplicar filtros de forma otimizada
        
        tipo = self.request.query_params.get('enti_tipo_enti')
        search_query = self.request.query_params.get('search')
        
        # Filtro por empresa primeiro (mais eficiente)
        if empresa_id:
            queryset = queryset.filter(enti_empr=empresa_id)
        # Filtro por tipo de entidade (ex.: VE para vendedores)
        if tipo:
            queryset = queryset.filter(enti_tipo_enti=tipo)
        
        # Filtro de busca otimizado
        if search_query:
            queryset = queryset.filter(
                Q(enti_nome__icontains=search_query) |
                Q(enti_nume__icontains=search_query)
            )
        
        # Ordenação otimizada
        return queryset.order_by('enti_empr', 'enti_nome')

    def get_object(self):
        """
        Override get_object to handle duplicate records properly
        """
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        
        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        
        # Get additional filters from request parameters
        empr = self.request.GET.get('empr')
   
        
        if empr:
            filter_kwargs['enti_empr'] = empr
        
        # Use filter().first() instead of get() to handle duplicates
        obj = queryset.filter(**filter_kwargs).first()
        
        if not obj:
            from django.http import Http404
            raise Http404('No %s matches the given query.' % queryset.model._meta.object_name)
        
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        
        return obj

    def get_serializer_class(self):
        return EntidadesSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def perform_create(self, serializer):
        empresa_id = (
            self.request.data.get('enti_empr')
            or self.request.headers.get("X-Empresa")
            or self.request.session.get("empresa_id")
            or self.request.headers.get("Empresa_id")
        )
        try:
            empresa_id = int(empresa_id) if empresa_id is not None else None
        except Exception:
            pass
        serializer.save(enti_empr=empresa_id)

    def perform_update(self, serializer):
        instance = self.get_object()
        serializer.save(enti_empr=instance.enti_empr)

    @action(detail=False, methods=['get'], url_path='buscar-endereco')
    @modulo_necessario('Entidades')
    def buscar_endereco(self, request, slug=None):
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        
        cep = request.GET.get('cep')
        if not cep:
            return Response({"erro": "CEP não informado"}, status=400)

        # Cache para CEPs consultados
        cache_key = f"endereco_cep_{cep}"
        endereco = cache.get(cache_key)
        
        if not endereco:
            endereco = buscar_endereco_por_cep(cep)
            if endereco:
                cache.set(cache_key, endereco, 3600)  # Cache por 1 hora
        
        if endereco:
            return Response(endereco)
        else:
            return Response({"erro": "CEP inválido ou não encontrado"}, status=404)
        


    @action(detail=False, methods=['post'], url_path='cadastro-rapido-outros')
    def cadastro_rapido_outros(self, request, slug=None):
        serializer = EntidadesTipoOutrosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request)

        empresa_id = (
            request.data.get("enti_empr")
            or request.headers.get("X-Empresa")
            or request.session.get("empresa_id")
            or request.headers.get("Empresa_id")
        )

        filial_id = (
            request.headers.get("X-Filial")
            or request.session.get("filial_id")
            or request.headers.get("Filial_id")
        )

        if banco == 'demonstracao':
            cep_fallback = CEP_FALLBACK_DEMONSTRACAO
        elif banco in BANCOS_CEP_FIXO:
            cep_fallback = CEP_FALLBACK_PG_PISOS
        else:
            cep_fallback = None
        print(f"empresa_id: {empresa_id}, filial_id: {filial_id}, banco: {banco}, cep_fallback: {cep_fallback}")

        try:
            entidade = EntidadeServico.cadastrar_outros(
                data=serializer.validated_data,
                empresa_id=empresa_id,
                filial_id=filial_id,
                banco=banco,
                cep_fallback=cep_fallback
            )
            print(f"Entidade criada com sucesso: {entidade}")
            print(f"DEBUG enti_clie: {getattr(entidade, 'enti_clie', 'NÃO ENCONTRADO')}")
        except ValidationError as e:
            return Response(
                {"erro": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"enti_clie": entidade.enti_clie, "enti_nome": entidade.enti_nome},
            status=status.HTTP_201_CREATED
        )




from rest_framework.views import APIView
from django.db.models import Count

class EntidadesRelatorioAPI(APIView):
    
    def get(self, request, slug=None):
        empresa_param = request.GET.get("empresa")
        banco = None
        try:
            if slug:
                banco = get_db_from_slug(slug)
        except Exception:
            banco = None
        if not banco:
            try:
                banco = get_licenca_db_config(request)
            except Exception:
                banco = 'default'

        qs = Entidades.objects.using(banco).all()

        if empresa_param is None:
            empresa_sess = request.session.get("empresa_id") or request.headers.get("X-Empresa")
            empresa = empresa_sess
        else:
            empresa = empresa_param.strip()

        if empresa:
            qs = qs.filter(enti_empr=str(empresa))

        # ativos/inativos
        ativos = qs.filter(enti_situ='1').count()
        inativos = qs.filter(enti_situ='0').count()

        # agrupamento por tipo
        por_tipo = list(
            qs.values("enti_tipo_enti")
              .annotate(total=Count("enti_clie"))
              .order_by("-total")
        )

        listar = (request.GET.get("listar") or "").strip()
        situacao = (request.GET.get("situacao") or "").strip().lower()
        tipo = (request.GET.get("tipo") or "").strip()

        payload = {
            "ativos": ativos,
            "inativos": inativos,
            "por_tipo": por_tipo,
        }

        if listar == "situacao" and situacao in {"ativos", "inativos"}:
            alvo = '1' if situacao == 'ativos' else '0'
            entidades = list(
                qs.filter(enti_situ=alvo)
                  .values("enti_clie", "enti_nome", "enti_tipo_enti", "enti_emai", "enti_fone", "enti_celu", "enti_cida", "enti_esta")
                  .order_by("enti_nome")[:500]
            )
            payload["entidades"] = entidades
            payload["filtro"] = {"tipo": "situacao", "valor": situacao}

        elif listar == "tipo" and tipo:
            entidades = list(
                qs.filter(enti_tipo_enti=tipo)
                  .values("enti_clie", "enti_nome", "enti_tipo_enti", "enti_emai", "enti_fone", "enti_celu", "enti_cida", "enti_esta", "enti_situ")
                  .order_by("enti_nome")[:500]
            )
            payload["entidades"] = entidades
            payload["filtro"] = {"tipo": "tipo", "valor": tipo}

        return Response(payload)
