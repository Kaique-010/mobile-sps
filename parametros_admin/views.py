from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from .models import (
    PermissaoModulo,
    ConfiguracaoEstoque, ConfiguracaoFinanceiro, LogParametros
)
from .serializers import (
    PermissaoModuloSerializer,
    ConfiguracaoEstoqueSerializer,
    ConfiguracaoFinanceiroSerializer, LogParametrosSerializer
)
from .permissions import PermissaoAdministrador
from .utils import log_alteracao, get_modulo_by_name
import logging

logger = logging.getLogger(__name__)





class PermissaoModuloViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'parametros_admin'
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    serializer_class = PermissaoModuloSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['perm_empr', 'perm_fili', 'perm_modu__modu_nome', 'perm_ativ']
    search_fields = ['perm_modu__modu_nome', 'perm_obse']
    
    def get_queryset(self, slug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        return PermissaoModulo.objects.using(banco).all()
    
    def perform_create(self, serializer):
        banco = get_licenca_db_config(self.request)
        serializer.save(
            perm_usua_libe=self.request.user.usua_nome,
            using=banco
        )
    
    # Adicionar estes métodos na PermissaoModuloViewSet
    
    @action(detail=False, methods=['get'])
    def modulos_liberados(self, request, slug=None):
        slug = get_licenca_slug()
        """Retorna módulos liberados para a empresa do usuário"""
        try:
            empresa_id = getattr(request.user, 'usua_empr', 1)
            filial_id = getattr(request.user, 'usua_fili', 1)
            
            banco = get_licenca_db_config(request)
            modulos = PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_ativ=True
            ).values_list('perm_modu__modu_nome', flat=True)
            
            return Response({
                'modulos': list(modulos),
                'empresa_id': empresa_id,
                'filial_id': filial_id
            })
        except Exception as e:
            logger.error(f"Erro ao buscar módulos liberados: {e}")
            return Response(
                {'error': 'Erro ao buscar módulos liberados'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def permissoes_usuario(self, request,slug=None):
        slug = get_licenca_slug()

        """Retorna todas as permissões do usuário atual"""
        try:
            empresa_id = getattr(request.user, 'usua_empr', 1)
            filial_id = getattr(request.user, 'usua_fili', 1)
            
            banco = get_licenca_db_config(request)
            
            # Módulos liberados
            modulos = list(PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_ativ=True
            ).values_list('perm_modu__modu_nome', flat=True))
            
            # Configurações de estoque
            try:
                config_estoque = ConfiguracaoEstoque.objects.using(banco).get(
                    conf_empr=empresa_id,
                    conf_fili=filial_id
                )
                estoque_config = ConfiguracaoEstoqueSerializer(config_estoque).data
            except ConfiguracaoEstoque.DoesNotExist:
                estoque_config = {}
            
            # Configurações financeiras
            try:
                config_financeiro = ConfiguracaoFinanceiro.objects.using(banco).get(
                    conf_empr=empresa_id,
                    conf_fili=filial_id
                )
                financeiro_config = ConfiguracaoFinanceiroSerializer(config_financeiro).data
            except ConfiguracaoFinanceiro.DoesNotExist:
                financeiro_config = {}
            
            return Response({
                'modulos': modulos,
                'estoque': estoque_config,
                'financeiro': financeiro_config,
                'usuario': {
                    'empresa_id': empresa_id,
                    'filial_id': filial_id,
                    'nome': request.user.usua_nome
                }
            })
        except Exception as e:
            logger.error(f"Erro ao buscar permissões do usuário: {e}")
            return Response(
                {'error': 'Erro ao buscar permissões'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def configuracao_completa(self, request, slug=None):
        """Retorna configuração completa do sistema para o usuário"""
        slug = get_licenca_slug()
        try:
            empresa_id = getattr(request.user, 'usua_empr', 1)
            filial_id = getattr(request.user, 'usua_fili', 1)
            
            banco = get_licenca_db_config(request)
            
            # Módulos liberados
            modulos = list(PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_ativ=True
            ).values_list('perm_modu__modu_nome', flat=True))
            
            # Configurações de estoque
            try:
                config_estoque = ConfiguracaoEstoque.objects.using(banco).get(
                    conf_empr=empresa_id,
                    conf_fili=filial_id
                )
                estoque_config = ConfiguracaoEstoqueSerializer(config_estoque).data
            except ConfiguracaoEstoque.DoesNotExist:
                estoque_config = {}
            
            # Configurações financeiras
            try:
                config_financeiro = ConfiguracaoFinanceiro.objects.using(banco).get(
                    conf_empr=empresa_id,
                    conf_fili=filial_id
                )
                financeiro_config = ConfiguracaoFinanceiroSerializer(config_financeiro).data
            except ConfiguracaoFinanceiro.DoesNotExist:
                financeiro_config = {}
            
            # Parâmetros gerais (removido pois o modelo não existe)
            parametros_data = {}
            
            return Response({
                'modulos_liberados': modulos,
                'configuracao_estoque': estoque_config,
                'configuracao_financeiro': financeiro_config,
                'parametros_gerais': parametros_data,
                'usuario': {
                    'empresa_id': empresa_id,
                    'filial_id': filial_id,
                    'nome': request.user.usua_nome,
                    'id': request.user.usua_codi
                },
                'licenca': {
                    'slug': slug,
                    'banco': banco
                }
            })
        except Exception as e:
            logger.error(f"Erro ao buscar configuração completa: {e}")
            return Response(
                {'error': 'Erro ao buscar configuração completa'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def modulos_disponiveis(self, request, slug=None):
        
        slug = get_licenca_slug()
        """Lista todos os módulos do sistema"""
        from .utils import get_modulos_sistema
        modulos = get_modulos_sistema()
        return Response({'modulos': modulos})
    
    @action(detail=False, methods=['post'])
    def liberar_modulos_empresa(self, request,slug=None):
        
        slug = get_licenca_slug()
        """Libera módulos específicos para uma empresa"""
        empresa_id = request.data.get('empresa_id')
        filial_id = request.data.get('filial_id')
        modulos_selecionados = request.data.get('modulos', [])
        
        banco = get_licenca_db_config(request)
        
        # Remover liberações antigas
        PermissaoModulo.objects.using(banco).filter(
            perm_empr=empresa_id,
            perm_fili=filial_id
        ).delete()
        
        # Criar novas liberações
        liberados = 0
        for nome_modulo in modulos_selecionados:
            # Buscar o módulo pelo nome
            from .utils import get_modulo_by_name
            modulo_obj = get_modulo_by_name(nome_modulo)
            
            if modulo_obj:
                PermissaoModulo.objects.using(banco).create(
                    perm_empr=empresa_id,
                    perm_fili=filial_id,
                    perm_modu=modulo_obj,
                    perm_ativ=True,
                    perm_usua_libe=request.user.usua_nome
                )
                liberados += 1
            else:
                logger.warning(f"Módulo '{nome_modulo}' não encontrado no sistema")
        
        return Response({'message': f'{liberados} módulos liberados'})
    
    @action(detail=False, methods=['post'])
    def sincronizar_licenca(self, request, slug=None):
        
        slug = get_licenca_slug()
        """Sincroniza módulos com a licença atual"""
        try:
            banco = get_licenca_db_config(request)
            modulos_licenca = getattr(request, 'modulos_disponiveis', [])
            
            empr = request.data.get('perm_empr', 1)
            fili = request.data.get('perm_fili', 1)
            
            sincronizados = 0
            for nome_modulo in modulos_licenca:
                # Buscar o módulo pelo nome
                from .utils import get_modulo_by_name
                modulo_obj = get_modulo_by_name(nome_modulo)
                
                if modulo_obj:
                    obj, created = PermissaoModulo.objects.using(banco).get_or_create(
                        perm_empr=empr,
                        perm_fili=fili,
                        perm_modu=modulo_obj,
                        defaults={
                            'perm_ativ': True,
                            'perm_usua_libe': request.user.usua_nome,
                            'perm_obse': 'Sincronizado automaticamente'
                        }
                    )
                    if created:
                        sincronizados += 1
                else:
                    logger.warning(f"Módulo '{nome_modulo}' não encontrado no sistema")
            
            return Response({
                'message': f'{sincronizados} módulos sincronizados',
                'sincronizados': sincronizados
            })
        except Exception as e:
            logger.error(f"Erro ao sincronizar módulos: {e}")
            return Response(
                {'error': 'Erro ao sincronizar módulos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def modulos_empresa_filial(self, request, slug=None):
        """Retorna módulos liberados para uma empresa/filial específica"""
        try:
            empresa_id = request.query_params.get('empresa_id', 1)
            filial_id = request.query_params.get('filial_id', 1)
            
            banco = get_licenca_db_config(request)
            from .utils import get_modulos_liberados_empresa
            
            modulos_liberados = get_modulos_liberados_empresa(banco, empresa_id, filial_id)
            
            return Response({
                'empresa_id': empresa_id,
                'filial_id': filial_id,
                'modulos_liberados': modulos_liberados,
                'total_modulos': len(modulos_liberados)
            })
        except Exception as e:
            logger.error(f"Erro ao buscar módulos da empresa/filial: {e}")
            return Response(
                {'error': 'Erro ao buscar módulos da empresa/filial'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def configurar_modulos_empresa(self, request, slug=None):
        """Configura módulos liberados para uma empresa/filial"""
        try:
            empresa_id = request.data.get('empresa_id')
            filial_id = request.data.get('filial_id')
            modulos_selecionados = request.data.get('modulos', [])
            
            if not empresa_id or not filial_id:
                return Response(
                    {'error': 'empresa_id e filial_id são obrigatórios'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            banco = get_licenca_db_config(request)
            
            # Remover permissões existentes para esta empresa/filial
            PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id
            ).delete()
            
            # Criar novas permissões
            liberados = 0
            for nome_modulo in modulos_selecionados:
                modulo_obj = get_modulo_by_name(nome_modulo)
                
                if modulo_obj:
                    PermissaoModulo.objects.using(banco).create(
                        perm_empr=empresa_id,
                        perm_fili=filial_id,
                        perm_modu=modulo_obj,
                        perm_ativ=True,
                        perm_usua_libe=request.user.usua_nome
                    )
                    liberados += 1
                else:
                    logger.warning(f"Módulo '{nome_modulo}' não encontrado no sistema")
            
            return Response({
                'message': f'{liberados} módulos configurados para empresa {empresa_id}/filial {filial_id}',
                'liberados': liberados,
                'empresa_id': empresa_id,
                'filial_id': filial_id
            })
        except Exception as e:
            logger.error(f"Erro ao configurar módulos da empresa: {e}")
            return Response(
                {'error': 'Erro ao configurar módulos da empresa'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ConfiguracaoEstoqueViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'parametros_admin'
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    serializer_class = ConfiguracaoEstoqueSerializer
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return ConfiguracaoEstoque.objects.using(banco).all()
    
    def perform_update(self, serializer):
        banco = get_licenca_db_config(self.request)
        serializer.save(
            conf_usua_alte=self.request.user.usua_nome,
            using=banco
        )
        # Limpar cache
        from django.core.cache import cache
        cache.delete(f"estoque_config_{banco}")
    
    @action(detail=False, methods=['get'])
    def configuracao_atual(self, request):
        """Retorna a configuração atual de estoque"""
        config = getattr(request, 'estoque_config', {})
        return Response(config)

class ConfiguracaoFinanceiroViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'parametros_admin'
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    serializer_class = ConfiguracaoFinanceiroSerializer
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return ConfiguracaoFinanceiro.objects.using(banco).all()
    
    def perform_update(self, serializer):
        banco = get_licenca_db_config(self.request)
        serializer.save(
            conf_usua_alte=self.request.user.usua_nome,
            using=banco
        )
        # Limpar cache
        from django.core.cache import cache
        cache.delete(f"financeiro_config_{banco}")
    
    @action(detail=False, methods=['get'])
    def configuracao_atual(self, request):
        """Retorna a configuração atual financeira"""
        config = getattr(request, 'financeiro_config', {})
        return Response(config)

class LogParametrosViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    serializer_class = LogParametrosSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['log_tabe', 'log_acao', 'log_usua']
    ordering = ['-log_data']
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return LogParametros.objects.using(banco).all()
