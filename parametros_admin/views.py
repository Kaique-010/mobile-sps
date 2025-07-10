from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from core.decorator import ModuloRequeridoMixin
from core.middleware import get_licenca_slug
from core.utils import get_licenca_db_config
from .models import (PermissaoModulo,Modulo
)
from .serializers import (
    PermissaoModuloSerializer, ModuloSerializer

)
from .permissions import PermissaoAdministrador
from .utils import log_alteracao, get_modulo_by_name
import logging

logger = logging.getLogger(__name__)



class ModulosPorEmpresaView(generics.ListAPIView):
    serializer_class = ModuloSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        empresa = self.request.user.empresa_id
        filial = self.request.user.filial_id

        modulos = Modulo.objects.filter(modu_ativ=True).order_by('modu_ordem')

        permissoes = PermissaoModulo.objects.filter(
            perm_empr=empresa,
            perm_fili=filial,
        )

        # Cria um dict rápido para mapear módulo -> permissão
        permissoes_dict = {p.perm_modu_id: p.perm_ativ for p in permissoes}

        # Anexa a permissão a cada módulo (True/False)
        for modulo in modulos:
            modulo.perm_ativ = permissoes_dict.get(modulo.modu_codi, False)

        return modulos



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
            from .utils import get_modulos_liberados_empresa
            
            modulos = get_modulos_liberados_empresa(banco, empresa_id, filial_id)
            
            return Response({
                'modulos': modulos,
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


class AtualizaPermissoesModulosView(APIView):
    def get(self, request, slug=None):
        empresa_id = request.GET.get('empr')
        filial_id = request.GET.get('fili')
        
        if not all([empresa_id, filial_id]):
            return Response({"erro": "Empresa e filial são obrigatórias."}, status=400)
        
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"erro": "Banco não encontrado."}, status=404)
        
        try:
            # Converter para inteiro
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            
            # Buscar todos os módulos
            modulos = Modulo.objects.using(banco).all()
            
            modulos_data = []
            for modulo in modulos:
                # Verificar se existe permissão para este módulo
                try:
                    permissao = PermissaoModulo.objects.using(banco).get(
                        perm_empr=empresa_id,
                        perm_fili=filial_id,
                        perm_modu=modulo
                    )
                    ativo = permissao.perm_ativ
                except PermissaoModulo.DoesNotExist:
                    # Se não existe permissão, assume como inativo
                    ativo = False
                
                modulos_data.append({
                    "nome": modulo.modu_nome,
                    "ativo": ativo
                })
            
            return Response(modulos_data, status=200)
            
        except ValueError as e:
            return Response({"erro": f"Valores inválidos para empresa ou filial: {str(e)}"}, status=400)
        except Exception as e:
            return Response({"erro": str(e)}, status=500)
    
    def patch(self, request, slug=None):
        data = request.data
        empresa_id = data.get("empr")
        filial_id = data.get("fili")
        usuario = data.get("usuario", "sistema")
        modulos_data = data.get("modulos", [])

        if not all([empresa_id, filial_id, modulos_data]):
            return Response({"erro": "Dados incompletos."}, status=400)

        try:
           
            
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            usuario = int(usuario)

        except ValueError as e:
            return Response({"erro": f"Valores inválidos para empresa ou filial: {str(e)}"}, status=400)

        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"erro": "Banco não encontrado."}, status=404)

        atualizados = 0
        for item in modulos_data:
            nome = item.get("nome")
            ativo = item.get("ativo", False)
            try:
                modulo = Modulo.objects.using(banco).get(modu_nome=nome)
                obj, created = PermissaoModulo.objects.using(banco).update_or_create(
                    perm_empr=empresa_id,
                    perm_fili=filial_id,
                    perm_modu=modulo,
                    defaults={
                        "perm_ativ": ativo,
                        "perm_usua_libe": usuario
                    }
                )
                atualizados += 1
            except Modulo.DoesNotExist:
                continue  # ignora se o módulo não existir
            except Exception as e:
                logger.error(f"Erro ao atualizar módulo {nome}: {e}")
                continue

        return Response({
            "mensagem": f"Permissões atualizadas com sucesso ({atualizados})"
        }, status=200)