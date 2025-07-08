from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from .models import (
    ParametrosGerais, PermissoesModulos, PermissoesRotas,
    ConfiguracaoEstoque, ConfiguracaoFinanceiro, LogParametros
)
from .serializers import (
    ParametrosGeraisSerializer, PermissoesModulosSerializer,
    PermissoesRotasSerializer, ConfiguracaoEstoqueSerializer,
    ConfiguracaoFinanceiroSerializer, LogParametrosSerializer
)
from .permissions import PermissaoAdministrador
from .utils import log_alteracao
import logging

logger = logging.getLogger(__name__)

class ParametrosGeraisViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'parametros_admin'
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    serializer_class = ParametrosGeraisSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['para_empr', 'para_fili', 'para_tipo', 'para_ativ']
    search_fields = ['para_nome', 'para_desc']
    ordering_fields = ['para_nome', 'para_data_alte']
    ordering = ['para_nome']
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        return ParametrosGerais.objects.using(banco).all()
    
    def perform_create(self, serializer):
        banco = get_licenca_db_config(self.request)
        instance = serializer.save(
            para_usua_alte=self.request.user.usua_nome,
            using=banco
        )
        log_alteracao('parametros_gerais', instance.para_codi, 'create', 
                     None, serializer.data, self.request.user.usua_nome, 
                     self.request.META.get('REMOTE_ADDR'))
    
    def perform_update(self, serializer):
        banco = get_licenca_db_config(self.request)
        old_data = ParametrosGeraisSerializer(serializer.instance).data
        instance = serializer.save(
            para_usua_alte=self.request.user.usua_nome,
            using=banco
        )
        log_alteracao('parametros_gerais', instance.para_codi, 'update',
                     old_data, serializer.data, self.request.user.usua_nome,
                     self.request.META.get('REMOTE_ADDR'))
    
    @action(detail=False, methods=['post'])
    def importar_padrao(self, request):
        """Importa parâmetros padrão do sistema"""
        try:
            banco = get_licenca_db_config(request)
            parametros_padrao = self._get_parametros_padrao()
            
            criados = 0
            for param in parametros_padrao:
                param['para_empr'] = request.data.get('para_empr', 1)
                param['para_fili'] = request.data.get('para_fili', 1)
                
                obj, created = ParametrosGerais.objects.using(banco).get_or_create(
                    para_empr=param['para_empr'],
                    para_fili=param['para_fili'],
                    para_nome=param['para_nome'],
                    defaults=param
                )
                if created:
                    criados += 1
            
            return Response({
                'message': f'{criados} parâmetros padrão importados com sucesso',
                'criados': criados
            })
        except Exception as e:
            logger.error(f"Erro ao importar parâmetros padrão: {e}")
            return Response(
                {'error': 'Erro ao importar parâmetros padrão'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_parametros_padrao(self):
        """Retorna lista de parâmetros padrão do sistema"""
        return [
            {
                'para_nome': 'sistema_nome',
                'para_valo': 'Sistema SPS',
                'para_tipo': 'string',
                'para_desc': 'Nome do sistema'
            },
            {
                'para_nome': 'backup_automatico',
                'para_valo': 'true',
                'para_tipo': 'boolean',
                'para_desc': 'Realizar backup automático'
            },
            {
                'para_nome': 'dias_backup',
                'para_valo': '7',
                'para_tipo': 'integer',
                'para_desc': 'Dias para manter backup'
            },
            {
                'para_nome': 'email_notificacoes',
                'para_valo': 'true',
                'para_tipo': 'boolean',
                'para_desc': 'Enviar notificações por email'
            }
        ]

class PermissoesModulosViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'parametros_admin'
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    serializer_class = PermissoesModulosSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['perm_empr', 'perm_fili', 'perm_modu', 'perm_ativ']
    search_fields = ['perm_modu', 'perm_obse']
    
    def get_queryset(self, slug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        return PermissoesModulos.objects.using(banco).all()
    
    def perform_create(self, serializer):
        banco = get_licenca_db_config(self.request)
        serializer.save(
            perm_usua_libe=self.request.user.usua_nome,
            using=banco
        )
    
    # Adicionar estes métodos na PermissoesModulosViewSet:
    
    @action(detail=False, methods=['get'])
    def modulos_liberados(self, request):
        """Retorna módulos liberados para a empresa do usuário"""
        try:
            empresa_id = getattr(request.user, 'usua_empr', 1)
            filial_id = getattr(request.user, 'usua_fili', 1)
            
            banco = get_licenca_db_config(request)
            modulos = PermissoesModulos.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_ativ=True
            ).values_list('perm_modu', flat=True)
            
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
            modulos = list(PermissoesModulos.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_ativ=True
            ).values_list('perm_modu', flat=True))
            
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
        PermissoesModulos.objects.using(banco).filter(
            perm_empr=empresa_id,
            perm_fili=filial_id
        ).delete()
        
        # Criar novas liberações
        for modulo in modulos_selecionados:
            PermissoesModulos.objects.using(banco).create(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_modu=modulo,
                perm_ativ=True,
                perm_usua_libe=request.user.usua_nome
            )
        
        return Response({'message': f'{len(modulos_selecionados)} módulos liberados'})
    
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
            for modulo in modulos_licenca:
                obj, created = PermissoesModulos.objects.using(banco).get_or_create(
                    perm_empr=empr,
                    perm_fili=fili,
                    perm_modu=modulo,
                    defaults={
                        'perm_ativ': True,
                        'perm_usua_libe': request.user.usua_nome,
                        'perm_obse': 'Sincronizado automaticamente'
                    }
                )
                if created:
                    sincronizados += 1
            
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

class ConfiguracaoEstoqueViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'parametros_admin'
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
    modulo_necessario = 'parametros_admin'
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
