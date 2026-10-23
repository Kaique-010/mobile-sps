from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from django.core.exceptions import ValidationError  
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework import status
from rest_framework.views import APIView
from django.db.models import Count
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.utils import get_db_from_slug
from .models import Entidades
from .serializers import EntidadesSerializer, EntidadesTipoOutrosSerializer, EntidadesCadastroRapidoCreateSerializer
from .utils import buscar_endereco_por_cep
from django.db.models import Q
from django.core.cache import cache
from .services.entidades_tipooutros import EntidadeServico
from .services.cadastro_rapido import EntidadeCadastroRapido
from .services.cadastro_rapido_simplificado import EntidadeCadastroRapidoSimplificado
from .services.relatorio import EntidadesRelatorioService
from .services.entidades_filters import apply_vinculo_filters


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
    filterset_fields = ['enti_empr', 'enti_tipo_enti', 'enti_espe_enti', 'enti_situ']

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
        classificacao = self.request.query_params.get('enti_espe_enti')
        situacao = self.request.query_params.get('enti_situ')
        search_query = self.request.query_params.get('search')
        
        
        # Filtro por empresa primeiro (mais eficiente)
        if empresa_id:
            queryset = queryset.filter(enti_empr=empresa_id)
        # Filtro por tipo de entidade (ex.: VE para vendedores)
        if tipo:
            queryset = queryset.filter(enti_tipo_enti=tipo)
        if classificacao:
            queryset = queryset.filter(enti_espe_enti=classificacao)
        if situacao:
            queryset = queryset.filter(enti_situ=situacao)
        
        # Filtro de busca otimizado
        if search_query:
            queryset = queryset.filter(
                Q(enti_nome__icontains=search_query) |
                Q(enti_nume__icontains=search_query)
            )
        
        # Filtro por vínculo com vendedor / arquiteto (query params 'has_vendedor' / 'has_arquiteto')
        has_vendedor = self.request.query_params.get('has_vendedor')
        has_arquiteto = self.request.query_params.get('has_arquiteto')
        if has_vendedor or has_arquiteto:
            queryset = apply_vinculo_filters(queryset, has_vendedor=has_vendedor, has_arquiteto=has_arquiteto)

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
        """Adiciona contexto com banco e flags para suportar arquiteto_responsavel quando serializando."""
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        # Flag para serializers saberem que devem incluir/permitir campos relacionados ao arquiteto/responsavel
        context['include_enti_arqu'] = True
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
        # Se o cliente informar o arquiteto via API, ele virá em request.data['enti_arqu'] e será salvo
        serializer.save(enti_empr=empresa_id)

    def perform_update(self, serializer):
        instance = self.get_object()
        serializer.save(enti_empr=instance.enti_empr)

    def get_serializer_context(self):
        """Adiciona contexto com banco e flags para suportar arquiteto_responsavel quando serializando."""
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def perform_create(self, serializer):
        # Permite que o campo enti_arqu seja salvo via API quando informado
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
        
    
    @action(detail=False, methods=['post'], url_path='cadastro-rapido')
    def cadastro_rapido(self, request, slug=None):
        serializer = EntidadesCadastroRapidoCreateSerializer(data=request.data)
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
        print(f"empresa_id: {empresa_id}, banco: {banco}, cep_fallback: {cep_fallback}")

        try:
            # Usar service simplificado se CPF não for fornecido
            cpf = serializer.validated_data.get("enti_cpf") or None
            if not cpf:
                entidade = EntidadeCadastroRapidoSimplificado.cadastrar_rapido_simplificado(
                    data=serializer.validated_data,
                    empresa_id=empresa_id,
                    banco=banco,
                )
            else:
                entidade = EntidadeCadastroRapido.cadastrar_rapido(
                    data=serializer.validated_data,
                    empresa_id=empresa_id,
                    banco=banco,
                    cep_fallback=cep_fallback if not serializer.validated_data.get("enti_cep") else None,
                    cpf=cpf,
                    email=serializer.validated_data.get("enti_emai"),
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





class EntidadesRelatorioAPI(APIView):
 
    @staticmethod
    def _resolver_banco(request, slug):
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
        return banco
 
    def get(self, request, slug=None):
        banco = self._resolver_banco(request, slug)
 
        empresa = request.GET.get("empresa")
        if empresa is None:
            empresa = request.session.get("empresa_id") or request.headers.get("X-Empresa")
 
        try:
            situacao = EntidadesRelatorioService.normalizar_situacao(request.GET.get("situacao"))
            meses = EntidadesRelatorioService.normalizar_meses(request.GET.get("meses"))
        except ValueError as e:
            return Response({"erro": str(e)}, status=status.HTTP_400_BAD_REQUEST)
 
        payload = EntidadesRelatorioService.gerar(
            banco=banco,
            empresa=empresa,
            situacao=situacao,
            meses=meses,
            tipo=(request.GET.get("tipo") or "").strip(),
            busca=request.GET.get("busca"),
        )
        return Response(payload)