from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework import status
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from .models import Entidades
from .serializers import EntidadesSerializer
from .utils import buscar_endereco_por_cep
from django.db.models import Q
from django.core.cache import cache

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
            
        # Base queryset otimizada
        queryset = Entidades.objects.using(banco).all()
        
        # Aplicar filtros de forma otimizada
        empresa_id = self.request.query_params.get('enti_empr')
        search_query = self.request.query_params.get('search')
        
        # Filtro por empresa primeiro (mais eficiente)
        if empresa_id:
            queryset = queryset.filter(enti_empr=empresa_id)
            
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
        fili = self.request.GET.get('fili')
        
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



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from Entidades.models import Entidades 
from django.db.models import Q
from core.registry import get_licenca_db_config, LICENCAS_MAP
from django.conf import settings
from django.db import connections
from decouple import config
import logging
from rest_framework.decorators import action
import jwt
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EntidadesLoginViewSet(viewsets.ViewSet):
    def create(self, request, slug=None):
        data = request.data
        documento = data.get('documento')  
        usuario = data.get('usuario')     
        senha = data.get('senha')        

        logger.info(f"[LOGIN CLIENTE ATTEMPT] {data}")

        if not documento or not usuario or not senha:
            return Response({"erro": "Documento, usuário e senha são obrigatórios"}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar em todas as licenças disponíveis
        for licenca in LICENCAS_MAP:
            try:
                banco_slug = licenca['slug']
                logger.info(f"[TENTANDO BANCO] {banco_slug}")
                
                # Configurar banco se não existir
                if banco_slug not in settings.DATABASES:
                    self._configurar_banco(licenca)
                
                # Buscar entidade neste banco
                entidade = Entidades.objects.using(banco_slug).get(
                    Q(enti_cpf=documento) | Q(enti_cnpj=documento)
                )
                
                logger.info(f"[ENTIDADE ENCONTRADA] Banco: {banco_slug}, ID: {entidade.enti_clie}")
                
                # Verificar credenciais
                if entidade.enti_mobi_usua == usuario and entidade.enti_mobi_senh == senha:
                    # Gerar tokens JWT customizados para entidades
                    access_token = self._gerar_access_token(entidade, banco_slug)
                    refresh_token = self._gerar_refresh_token(entidade, banco_slug)
                    
                    
                    # Log successful login
                    logger.info(f"[LOGIN SUCCESS] Cliente {entidade.enti_nome} logado no banco {banco_slug}")
                    
                    # Get document based on CPF or CNPJ
                    documento = entidade.enti_cpf if entidade.enti_cpf else entidade.enti_cnpj
                    
                    return Response({
                        'refresh': refresh_token,
                        'access': access_token,
                        'cliente_id': entidade.enti_clie,
                        'cliente_nome': entidade.enti_nome,
                        'documento': documento,               
                        'banco': banco_slug
                    })
                else:
                    logger.warning(f"[CREDENCIAIS INVÁLIDAS] Banco: {banco_slug}, Documento: {documento}")
                    
            except Entidades.DoesNotExist:
                logger.debug(f"[DOCUMENTO NÃO ENCONTRADO] Banco: {banco_slug}, Documento: {documento}")
                continue
            except Exception as e:
                logger.error(f"[ERRO BANCO {banco_slug}] {str(e)}")
                continue
        
        logger.error(f"[LOGIN FAILED] Documento {documento} não encontrado em nenhum banco")
        return Response({"erro": "Documento inválido"}, status=status.HTTP_400_BAD_REQUEST)
    
    def _gerar_access_token(self, entidade, banco):
        """Gera token de acesso customizado para entidades"""
        payload = {
            'cliente_id': entidade.enti_clie,
            'cliente_nome': entidade.enti_nome,
            'banco': banco,
            'tipo': 'cliente',
            'exp': datetime.utcnow() + timedelta(minutes=60),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    
    def _gerar_refresh_token(self, entidade, banco):
        """Gera token de refresh customizado para entidades"""
        payload = {
            'cliente_id': entidade.enti_clie,
            'banco': banco,
            'tipo': 'cliente_refresh',
            'exp': datetime.utcnow() + timedelta(days=7),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    
    def _configurar_banco(self, licenca):
        """Configura banco dinamicamente"""
        prefixo = licenca["slug"].upper()
        try:
            db_user = config(f"{prefixo}_DB_USER")
            db_password = config(f"{prefixo}_DB_PASSWORD")
            
            settings.DATABASES[licenca["slug"]] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': licenca["db_name"],
                'USER': db_user,
                'PASSWORD': db_password,
                'HOST': licenca["db_host"],
                'PORT': licenca["db_port"],
                'OPTIONS': {
                    'options': '-c timezone=America/Araguaina'
                },
            }
            
            connections.ensure_defaults(licenca["slug"])
            
        except Exception as e:
            logger.error(f"[ERRO CONFIGURAÇÃO BANCO] {licenca['slug']}: {str(e)}")
            raise


class EntidadesRefreshViewSet(viewsets.ViewSet):
    def create(self, request, slug=None):
        """Endpoint para renovar token de acesso usando refresh token"""
        refresh_token = request.data.get('refresh_token') or request.data.get('refresh')
        
        if not refresh_token:
            return Response({"erro": "Refresh token é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Decodificar o refresh token
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Verificar se é um refresh token válido
            if payload.get('tipo') != 'cliente_refresh':
                return Response({"erro": "Token inválido"}, status=status.HTTP_401_UNAUTHORIZED)
            
            cliente_id = payload.get('cliente_id')
            banco = payload.get('banco')
            
            # Configurar banco dinamicamente se necessário
            if banco not in settings.DATABASES:
                self._configurar_banco(banco)
            
            # Buscar a entidade no banco correto
            entidade = Entidades.objects.using(banco).get(enti_clie=cliente_id)
            
            # Gerar novo access token
            access_token = self._gerar_access_token(entidade, banco)
            
            logger.info(f"[REFRESH SUCCESS] Token renovado para cliente {cliente_id} no banco {banco}")
            
            return Response({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600
            }, status=status.HTTP_200_OK)
            
        except jwt.ExpiredSignatureError:
            logger.warning("[REFRESH EXPIRED] Refresh token expirado")
            return Response({"erro": "Token expirado"}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            logger.warning("[REFRESH INVALID] Token inválido")
            return Response({"erro": "Token inválido"}, status=status.HTTP_401_UNAUTHORIZED)
        except Entidades.DoesNotExist:
            logger.warning(f"[REFRESH ERROR] Cliente não encontrado - ID: {cliente_id}")
            return Response({"erro": "Cliente não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"[REFRESH ERROR] {str(e)}")
            return Response({"erro": "Erro interno"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _gerar_access_token(self, entidade, banco):
        """Gera token de acesso customizado para entidades"""
        payload = {
            'cliente_id': entidade.enti_clie,
            'cliente_nome': entidade.enti_nome,
            'banco': banco,
            'tipo': 'cliente',
            'exp': datetime.utcnow() + timedelta(minutes=60),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    def _configurar_banco(self, licenca):
        """Configura dinamicamente o banco de dados se não existir"""
        if licenca in LICENCAS_MAP:
            db_config = get_licenca_db_config(licenca)
            if db_config:
                settings.DATABASES[licenca] = {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': db_config['NAME'],
                    'USER': config('DB_USER'),
                    'PASSWORD': config('DB_PASSWORD'),
                    'HOST': db_config['HOST'],
                    'PORT': db_config['PORT'],
                }
                # Garantir que a conexão seja estabelecida
                connections.databases[licenca] = settings.DATABASES[licenca]
                logger.info(f"[CONFIG] Banco {licenca} configurado dinamicamente")
            else:
                logger.error(f"[CONFIG ERROR] Configuração não encontrada para licença: {licenca}")
        else:
            logger.error(f"[CONFIG ERROR] Licença não encontrada no mapeamento: {licenca}")