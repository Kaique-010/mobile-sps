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
from .models import (PermissaoModulo, Modulo, ParametroSistema)
from .permissions import PermissaoAdministrador
from .utils import get_modulo_by_name
from django.core.cache import cache
import logging
from .serializers import (PermissaoModuloSerializer, ModuloSerializer, ParametroSistemaSerializer)


logger = logging.getLogger(__name__)




class PermissaoModuloViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_requerido = 'parametros_admin'
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    serializer_class = PermissaoModuloSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['perm_empr', 'perm_fili', 'perm_modu__modu_nome', 'perm_ativ']
    search_fields = ['perm_modu__modu_nome']
    
    def get_queryset(self, slug=None):
        slug = get_licenca_slug()
        banco = get_licenca_db_config(self.request)
        return PermissaoModulo.objects.using(banco).all()
    
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['banco'] = get_licenca_db_config(self.request)
        ctx['usuario_id'] = getattr(self.request.user, 'usua_codi', 0)
        return ctx

    def perform_create(self, serializer):
        serializer.save(
            perm_usua_libe=getattr(self.request.user, 'usua_codi', 0),
        )
    
    # Adicionar estes métodos na PermissaoModuloViewSet
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def modulos_liberados(self, request, slug=None):
        """Retorna módulos liberados para a empresa do usuário"""
        try:
            # Priorizar cabeçalhos sobre query params
            empresa_id = request.META.get('HTTP_X_EMPRESA') or request.query_params.get('empr')
            filial_id = request.META.get('HTTP_X_FILIAL') or request.query_params.get('fili')
            
            # Fallback para valores do usuário
            if not empresa_id:
                empresa_id = getattr(request.user, 'usua_empr', 1)
            if not filial_id:
                filial_id = getattr(request.user, 'usua_fili', 1)
            
            # Converter para inteiro
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            
            print(f"🔍 [VIEW] modulos_liberados - Empresa: {empresa_id}, Filial: {filial_id}")
            
            banco = get_licenca_db_config(request)
            from .utils import get_codigos_modulos_liberados
            
            modulos_liberados = get_codigos_modulos_liberados(banco, empresa_id, filial_id)
            
            response_data = {
                'modulos_liberados': modulos_liberados,
                'empresa_id': empresa_id,
                'filial_id': filial_id
            }
            
            print(f"🔍 [VIEW] Retornando: {response_data}")
            
            return Response(response_data)
        except Exception as e:
            logger.error(f"Erro ao buscar módulos liberados: {e}")
            return Response(
                {'error': 'Erro ao buscar módulos liberados'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def modulos_disponiveis(self, request, slug=None):
        
        slug = get_licenca_slug()
        """Lista todos os módulos do sistema"""
        try:
            banco = get_licenca_db_config(request)
            from .utils import get_modulos_globais
            modulos = get_modulos_globais(banco)
            return Response({'modulos': modulos})
        except Exception as e:
            logger.error(f"Erro ao buscar módulos disponíveis: {e}")
            return Response({'modulos': []})
    
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
            modulo_obj = get_modulo_by_name(nome_modulo, banco)
            
            if modulo_obj:
                    PermissaoModulo.objects.using(banco).create(
                        perm_empr=empresa_id,
                        perm_fili=filial_id,
                        perm_modu=modulo_obj,
                        perm_ativ=True,
                        perm_usua_libe=getattr(request.user, 'usua_codi', 0)
                    )
                    liberados += 1
            else:
                logger.warning(f"Módulo '{nome_modulo}' não encontrado no sistema")
        try:
            cache.delete(f"modulos_licenca_{slug}_{empresa_id}_{filial_id}")
        except Exception:
            pass
        
        return Response({'message': f'{liberados} módulos liberados'})
    
    @action(detail=False, methods=['post'])
    def sincronizar_licenca(self, request, slug=None):
        
        slug = get_licenca_slug()
        """Sincroniza módulos com a licença atual"""
        try:
            banco = get_licenca_db_config(request)
            def _to_int(v, default=None):
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return default
            empr = _to_int(request.headers.get('X-Empresa')) or _to_int(request.data.get('perm_empr')) or request.session.get('empresa_id') or _to_int(getattr(request.user, 'usua_empr', None), 1) or 1
            fili = _to_int(request.headers.get('X-Filial')) or _to_int(request.data.get('perm_fili')) or request.session.get('filial_id') or _to_int(getattr(request.user, 'usua_fili', None), 1) or 1

            # Garantir sincronização dos módulos instalados no banco do slug
            Modulo.sync_installed_apps(alias=banco, force=False)
            modulos_qs = Modulo.objects.using(banco).all().order_by('modu_orde', 'modu_nome')
            from .utils import sync_permissoes_com_modulos
            criadas, existentes = sync_permissoes_com_modulos(
                banco,
                empr,
                fili,
                usuario_id=getattr(request.user, 'usua_codi', 0),
                default_ativ=False,
            )
            
            sincronizados = 0
            for modulo_obj in modulos_qs:
                obj, created = PermissaoModulo.objects.using(banco).get_or_create(
                    perm_empr=empr,
                    perm_fili=fili,
                    perm_modu=modulo_obj,
                    defaults={
                        'perm_ativ': True,
                        'perm_usua_libe': getattr(request.user, 'usua_codi', 0),
                    }
                )
                if created:
                    sincronizados += 1
                else:
                    if obj.perm_ativ is False:
                        obj.perm_ativ = True
                        obj.perm_usua_libe = getattr(request.user, 'usua_codi', 0)
                        obj.save(using=banco)
            try:
                cache.delete(f"modulos_licenca_{slug}_{empr}_{fili}")
            except Exception:
                pass
            
            return Response({
                'message': f'{sincronizados} módulos sincronizados; {criadas} permissões criadas',
                'sincronizados': sincronizados,
                'permissoes_criadas': criadas,
                'permissoes_existentes': existentes,
            })
        except Exception as e:
            logger.error(f"Erro ao sincronizar módulos: {e}")
            return Response(
                {'error': 'Erro ao sincronizar módulos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def modulos_empresa_filial(self, request, slug=None):
        """Retorna módulos liberados para uma empresa/filial específica"""
        try:
            # Tenta obter dos query params e converter para int
            def _to_int(value):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None

            empresa_id = _to_int(request.query_params.get('empresa_id'))
            filial_id = _to_int(request.query_params.get('filial_id'))

            # Fallback para sessão quando não informado ou inválido
            if empresa_id is None:
                empresa_id = request.session.get('empresa_id')
            if filial_id is None:
                filial_id = request.session.get('filial_id')

            # Fallback para cabeçalhos quando sessão não possui
            if empresa_id is None:
                empresa_id = _to_int(request.headers.get('X-Empresa'))
            if filial_id is None:
                filial_id = _to_int(request.headers.get('X-Filial'))

            # Último fallback para 1/1 para manter compatibilidade legada
            if empresa_id is None:
                empresa_id = 1
            if filial_id is None:
                filial_id = 1
            
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
                modulo_obj = get_modulo_by_name(nome_modulo, banco)
                
                if modulo_obj:
                    PermissaoModulo.objects.using(banco).create(
                        perm_empr=empresa_id,
                        perm_fili=filial_id,
                        perm_modu=modulo_obj,
                        perm_ativ=True,
                        perm_usua_libe=getattr(request.user, 'usua_codi', 0)
                    )
                    liberados += 1
                else:
                    logger.warning(f"Módulo '{nome_modulo}' não encontrado no sistema")
            try:
                slug_val = get_licenca_slug()
                cache.delete(f"modulos_licenca_{slug_val}_{empresa_id}_{filial_id}")
            except Exception:
                pass
            
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

    @action(detail=False, methods=['get'])
    def permissoes_usuario(self, request, slug=None):
        """Retorna permissões de módulos para o usuário atual"""
        try:
            empresa_id = request.META.get('HTTP_X_EMPRESA') or request.query_params.get('empr')
            filial_id = request.META.get('HTTP_X_FILIAL') or request.query_params.get('fili')
            
            if not empresa_id:
                empresa_id = getattr(request.user, 'usua_empr', 1)
            if not filial_id:
                filial_id = getattr(request.user, 'usua_fili', 1)
            
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            
            banco = get_licenca_db_config(request)
            
            permissoes = PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_ativ=True
            ).select_related('perm_modu')
            
            modulos_permitidos = []
            for perm in permissoes:
                modulos_permitidos.append({
                    'codigo': perm.perm_modu.modu_codi,
                    'nome': perm.perm_modu.modu_nome,
                    'ativo': perm.perm_ativ
                })
            
            return Response({
                'empresa_id': empresa_id,
                'filial_id': filial_id,
                'permissoes': modulos_permitidos
            })
            
        except Exception as e:
            logger.error(f"Erro ao obter permissões do usuário: {e}")
            return Response(
                {'error': 'Erro ao obter permissões do usuário'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def verificar_permissao(self, request, tela=None, operacao=None, slug=None):
        """Verifica se o usuário tem permissão para uma tela/operação específica"""
        try:
            empresa_id = request.META.get('HTTP_X_EMPRESA') or request.query_params.get('empr')
            filial_id = request.META.get('HTTP_X_FILIAL') or request.query_params.get('fili')
            
            if not empresa_id:
                empresa_id = getattr(request.user, 'usua_empr', 1)
            if not filial_id:
                filial_id = getattr(request.user, 'usua_fili', 1)
            
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            
            banco = get_licenca_db_config(request)
            
            # Buscar módulo pela tela
            modulo = Modulo.objects.using(banco).filter(
                modu_nome__icontains=tela
            ).first()
            
            if not modulo:
                return Response({
                    'permitido': False,
                    'motivo': f'Módulo para tela {tela} não encontrado'
                })
            
            # Verificar permissão
            permissao_existe = PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_modu=modulo,
                perm_ativ=True
            ).exists()
            
            return Response({
                'permitido': permissao_existe,
                'tela': tela,
                'operacao': operacao,
                'modulo': modulo.modu_nome
            })
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão: {e}")
            return Response(
                {'permitido': False, 'erro': 'Erro ao verificar permissão'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AtualizaPermissoesModulosView(APIView):
    permission_classes = [IsAuthenticated, PermissaoAdministrador]

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
        empresa_id = data.get("empresa_id")  # ✅ Corrigido
        filial_id = data.get("filial_id")    # ✅ Corrigido
        usuario = data.get("usuario") or getattr(request.user, "usua_codi", 0)
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

                # Atualiza ou cria a permissão
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
                continue
            except Exception as e:
                logger.error(f"Erro ao atualizar módulo {nome}: {e}")
                continue

        try:
            slug_val = get_licenca_slug()
            cache.delete(f"modulos_licenca_{slug_val}_{empresa_id}_{filial_id}")
        except Exception:
            pass

        return Response({
            "mensagem": f"Permissões e módulos atualizados com sucesso ({atualizados})"
        }, status=200)



class ParametrosPorModuloView(APIView):
    """View para gerenciar parâmetros organizados por módulo"""
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    
    def get(self, request, slug=None):
        """Lista parâmetros organizados por módulo"""
        empresa_id = request.GET.get('empr')
        filial_id = request.GET.get('fili')
        
        if not all([empresa_id, filial_id]):
            return Response({"erro": "Empresa e filial são obrigatórias."}, status=400)
        
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"erro": "Banco não encontrado."}, status=404)
        
        try:
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            
            # Buscar módulos ativos
            modulos = Modulo.objects.using(banco).filter(modu_ativ=True).order_by('modu_orde')
            
            modulos_data = []
            for modulo in modulos:
                # Buscar parâmetros deste módulo
                parametros = ParametroSistema.objects.using(banco).filter(
                    para_empr=empresa_id,
                    para_fili=filial_id,
                    para_modu=modulo
                ).order_by('para_nome')
                
                parametros_data = []
                for param in parametros:
                    parametros_data.append({
                        'id': param.para_codi,
                        'nome': param.para_nome,
                        'descricao': param.para_desc,
                        'valor': param.para_valo,
                        'ativo': param.para_ativ
                    })
                
                modulos_data.append({
                    'id': modulo.modu_codi,
                    'nome': modulo.modu_nome,
                    'descricao': modulo.modu_desc,
                    'icone': modulo.modu_icon,
                    'parametros': parametros_data
                })
            
            return Response(modulos_data, status=200)
            
        except ValueError as e:
            return Response({"erro": f"Valores inválidos: {str(e)}"}, status=400)
        except Exception as e:
            logger.error(f"Erro ao buscar parâmetros por módulo: {e}")
            return Response({"erro": str(e)}, status=500)
    
    def patch(self, request, slug=None):
        """Atualiza status de parâmetros"""
        data = request.data
        empresa_id = data.get("empr")
        filial_id = data.get("fili")
        usuario = data.get("usuario", "sistema")
        parametros_data = data.get("parametros", [])

        if not all([empresa_id, filial_id, parametros_data]):
            return Response({"erro": "Dados incompletos."}, status=400)

        try:
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            usuario = int(usuario)
        except ValueError as e:
            return Response({"erro": f"Valores inválidos: {str(e)}"}, status=400)

        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"erro": "Banco não encontrado."}, status=404)

        atualizados = 0
        for item in parametros_data:
            param_id = item.get("id")
            ativo = item.get("ativo", False)
            
            try:
                parametro = ParametroSistema.objects.using(banco).get(
                    para_codi=param_id,
                    para_empr=empresa_id,
                    para_fili=filial_id
                )
                
                # Atualizar status
                parametro.para_ativ = ativo
                parametro.para_usua_alte = usuario
                parametro.save(using=banco)
                
                # Log da alteração
                from .models import LogParametroSistema
                LogParametroSistema.objects.using(banco).create(
                    log_para=parametro,
                    log_acao='ATIVACAO' if ativo else 'DESATIVACAO',
                    log_valo_ante=not ativo,
                    log_valo_novo=ativo,
                    log_usua=usuario,
                    log_empr=empresa_id,
                    log_fili=filial_id
                )
                
                atualizados += 1
                
            except ParametroSistema.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"Erro ao atualizar parâmetro {param_id}: {e}")
                continue

        return Response({
            "mensagem": f"Parâmetros atualizados com sucesso ({atualizados})"
        }, status=200)



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


class ParametroSistemaViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar parâmetros de sistema"""
    serializer_class = ParametroSistemaSerializer
    permission_classes = [IsAuthenticated, PermissaoAdministrador]
    
    def get_queryset(self):
        return ParametroSistema.objects.none()
    
    @action(detail=False, methods=['get', 'patch'])
    def parametros_estoque(self, request, slug=None):
        """Lista e atualiza parâmetros de estoque para uma empresa/filial"""
        if request.method == 'GET':
            try:
                empresa_id = request.GET.get('empr') or request.GET.get('empresa_id')
                filial_id = request.GET.get('fili') or request.GET.get('filial_id')
                
                if not empresa_id or not filial_id:
                    return Response(
                        {'error': 'empresa_id e filial_id são obrigatórios'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                banco = get_licenca_db_config(request)
                
                # Buscar módulos relacionados ao estoque
                modulos_estoque = Modulo.objects.using(banco).filter(
                    modu_nome__in=['Produtos', 'Entradas_Estoque', 'Saidas_Estoque'],
                    modu_ativ=True
                )
                
                if not modulos_estoque.exists():
                    return Response(
                        {'error': 'Módulos de estoque não encontrados'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Buscar TODOS os parâmetros dos módulos de estoque
                parametros_db = ParametroSistema.objects.using(banco).filter(
                    para_empr=empresa_id,
                    para_fili=filial_id,
                    para_modu__in=modulos_estoque,
                    para_ativ=True
                ).order_by('para_nome')
                
                parametros = []
                for param in parametros_db:
                    parametros.append({
                        'nome': param.para_nome,
                        'descricao': param.para_desc,
                        'valor': param.para_valo,
                        'ativo': param.para_ativ,
                        'modulo': param.para_modu.modu_nome
                    })
                
                return Response({
                    'empresa_id': empresa_id,
                    'filial_id': filial_id,
                    'modulos': [m.modu_nome for m in modulos_estoque],
                    'parametros': parametros
                })
                
            except Exception as e:
                logger.error(f"Erro ao buscar parâmetros de estoque: {e}")
                return Response(
                    {'error': 'Erro ao buscar parâmetros de estoque'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        elif request.method == 'PATCH':
            try:
                # Buscar empresa_id e filial_id no request.data para PATCH
                empresa_id = request.data.get('empresa_id') or request.GET.get('empr') or request.GET.get('empresa_id')
                filial_id = request.data.get('filial_id') or request.GET.get('fili') or request.GET.get('filial_id')
                
                if not empresa_id or not filial_id:
                    return Response(
                        {'error': 'empresa_id e filial_id são obrigatórios'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                banco = get_licenca_db_config(request)
                
                # Definir módulos de estoque
                modulos_estoque = Modulo.objects.using(banco).filter(
                    modu_nome__in=['Produtos', 'Entradas_Estoque', 'Saidas_Estoque']
                )
                
                if not modulos_estoque.exists():
                    return Response(
                        {'error': 'Módulos de estoque não encontrados'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Atualizar parâmetros
                parametros_atualizados = []
                for chave, valor in request.data.items():
                    # Pular campos de controle
                    if chave in ['empresa_id', 'filial_id']:
                        continue
                        
                    try:
                        # Buscar em todos os módulos de estoque
                        param = ParametroSistema.objects.using(banco).filter(
                            para_empr=empresa_id,
                            para_fili=filial_id,
                            para_modu__in=modulos_estoque,
                            para_nome=chave
                        ).first()
                        
                        if param:
                            param.para_valo = bool(valor)
                            param.para_usua_alte = request.user.usua_codi if hasattr(request.user, 'usua_codi') else 1
                            param.save(using=banco)
                            
                            parametros_atualizados.append({
                                'nome': param.para_nome,
                                'valor': param.para_valo,
                                'modulo': param.para_modu.modu_nome
                            })
                        else:
                            logger.warning(f"Parâmetro {chave} não encontrado nos módulos de estoque")
                            
                    except Exception as e:
                        logger.error(f"Erro ao atualizar parâmetro {chave}: {e}")
                        continue
                    
                return Response({
                    'message': 'Parâmetros atualizados com sucesso',
                    'parametros_atualizados': parametros_atualizados,
                    'empresa_id': empresa_id,
                    'filial_id': filial_id
                })
                
            except Exception as e:
                logger.error(f"Erro ao atualizar parâmetros de estoque: {e}")
                return Response(
                    {'error': 'Erro ao atualizar parâmetros de estoque'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    @action(detail=False, methods=['get'])
    def parametros_preco(self, request, slug=None):
        """Lista parâmetros de preço para uma empresa/filial"""
        try:
            empresa_id = request.GET.get('empresa_id')
            filial_id = request.GET.get('filial_id')
            
            if not empresa_id or not filial_id:
                return Response(
                    {'error': 'empresa_id e filial_id são obrigatórios'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            banco = get_licenca_db_config(request)
            
            # Buscar módulo de pedidos
            modulo_pedidos = Modulo.objects.using(banco).filter(
                modu_nome__icontains='pedido'
            ).first()
            
            if not modulo_pedidos:
                return Response(
                    {'error': 'Módulo de pedidos não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Parâmetros de preço
            parametros_preco = [
                'usar_preco_prazo',
                'usar_ultimo_preco'
            ]
            
            parametros = []
            for nome_param in parametros_preco:
                try:
                    param = ParametroSistema.objects.using(banco).get(
                        para_empr=empresa_id,
                        para_fili=filial_id,
                        para_modu=modulo_pedidos,
                        para_nome=nome_param
                    )
                    parametros.append({
                        'nome': param.para_nome,
                        'descricao': param.para_desc,
                        'valor': param.para_valo,
                        'ativo': param.para_ativ
                    })
                except ParametroSistema.DoesNotExist:
                    # Criar parâmetro com valor padrão
                    descricoes = {
                        'usar_preco_prazo': 'Usar preço de venda a prazo nos pedidos',
                        'usar_ultimo_preco': 'Usar último preço aplicado nos pedidos'
                    }
                    
                    param = ParametroSistema.objects.using(banco).create(
                        para_empr=empresa_id,
                        para_fili=filial_id,
                        para_modu=modulo_pedidos,
                        para_nome=nome_param,
                        para_desc=descricoes.get(nome_param, nome_param),
                        para_valo=False,
                        para_ativ=True,
                        para_usua_alte=request.user.usua_codi if hasattr(request.user, 'usua_codi') else 1
                    )
                    
                    parametros.append({
                        'nome': param.para_nome,
                        'descricao': param.para_desc,
                        'valor': param.para_valo,
                        'ativo': param.para_ativ
                    })
            
            return Response({
                'empresa_id': empresa_id,
                'filial_id': filial_id,
                'modulo': modulo_pedidos.modu_nome,
                'parametros': parametros
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar parâmetros de preço: {e}")
            return Response(
                {'error': 'Erro ao buscar parâmetros de preço'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def parametros_desconto(self, request, slug=None):
        """Lista parâmetros de desconto para uma empresa/filial"""
        try:
            empresa_id = request.GET.get('empresa_id')
            filial_id = request.GET.get('filial_id')
            
            if not empresa_id or not filial_id:
                return Response(
                    {'error': 'empresa_id e filial_id são obrigatórios'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            banco = get_licenca_db_config(request)
            
            # Buscar módulo de pedidos
            modulo_pedidos = Modulo.objects.using(banco).filter(
                modu_nome__icontains='pedido'
            ).first()
            
            if not modulo_pedidos:
                return Response(
                    {'error': 'Módulo de pedidos não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Parâmetros de desconto
            parametros_desconto = [
                'desconto_orcamento',
                'desconto_pedido'
            ]
            
            parametros = []
            for nome_param in parametros_desconto:
                try:
                    param = ParametroSistema.objects.using(banco).get(
                        para_empr=empresa_id,
                        para_fili=filial_id,
                        para_modu=modulo_pedidos,
                        para_nome=nome_param
                    )
                    parametros.append({
                        'nome': param.para_nome,
                        'descricao': param.para_desc,
                        'valor': param.para_valo,
                        'ativo': param.para_ativ
                    })
                except ParametroSistema.DoesNotExist:
                    # Criar parâmetro com valor padrão
                    descricoes = {
                        'desconto_orcamento': 'Permitir aplicar desconto em orçamentos',
                        'desconto_pedido': 'Permitir aplicar desconto em pedidos de venda'
                    }
                    
                    param = ParametroSistema.objects.using(banco).create(
                        para_empr=empresa_id,
                        para_fili=filial_id,
                        para_modu=modulo_pedidos,
                        para_nome=nome_param,
                        para_desc=descricoes.get(nome_param, nome_param),
                        para_valo=False,
                        para_ativ=True,
                        para_usua_alte=request.user.usua_codi if hasattr(request.user, 'usua_codi') else 1
                    )
                    
                    parametros.append({
                        'nome': param.para_nome,
                        'descricao': param.para_desc,
                        'valor': param.para_valo,
                        'ativo': param.para_ativ
                    })
            
            return Response({
                'empresa_id': empresa_id,
                'filial_id': filial_id,
                'modulo': modulo_pedidos.modu_nome,
                'parametros': parametros
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar parâmetros de desconto: {e}")
            return Response(
                {'error': 'Erro ao buscar parâmetros de desconto'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def atualizar_parametro(self, request, slug=None):
        """Atualiza um parâmetro específico"""
        try:
            empresa_id = request.data.get('empresa_id')
            filial_id = request.data.get('filial_id')
            nome_modulo = request.data.get('modulo')
            nome_parametro = request.data.get('parametro')
            valor = request.data.get('valor')
            
            if not all([empresa_id, filial_id, nome_modulo, nome_parametro]):
                return Response(
                    {'error': 'Todos os campos são obrigatórios'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            banco = get_licenca_db_config(request)
            
            # Buscar módulo
            modulo = Modulo.objects.using(banco).filter(
                modu_nome__icontains=nome_modulo
            ).first()
            
            if not modulo:
                return Response(
                    {'error': f'Módulo {nome_modulo} não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Atualizar parâmetro
            param = ParametroSistema.objects.using(banco).get(
                para_empr=empresa_id,
                para_fili=filial_id,
                para_modu=modulo,
                para_nome=nome_parametro
            )
            
            param.para_valo = bool(valor)
            param.para_usua_alte = request.user.usua_codi if hasattr(request.user, 'usua_codi') else 1
            param.save(using=banco)
            
            return Response({
                'message': f'Parâmetro {nome_parametro} atualizado com sucesso',
                'parametro': nome_parametro,
                'valor': param.para_valo
            })
            
        except ParametroSistema.DoesNotExist:
            return Response(
                {'error': 'Parâmetro não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar parâmetro: {e}")
            return Response(
                {'error': 'Erro ao atualizar parâmetro'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def verificar_permissao(self, request, tela=None, operacao=None, slug=None):
        """Verifica se o usuário tem permissão para uma tela/operação específica"""
        try:
            empresa_id = request.META.get('HTTP_X_EMPRESA') or request.query_params.get('empr')
            filial_id = request.META.get('HTTP_X_FILIAL') or request.query_params.get('fili')
            
            if not empresa_id:
                empresa_id = getattr(request.user, 'usua_empr', 1)
            if not filial_id:
                filial_id = getattr(request.user, 'usua_fili', 1)
            
            empresa_id = int(empresa_id)
            filial_id = int(filial_id)
            
            banco = get_licenca_db_config(request)
            
            # Buscar módulo pela tela
            modulo = Modulo.objects.using(banco).filter(
                modu_nome__icontains=tela
            ).first()
            
            if not modulo:
                return Response({
                    'permitido': False,
                    'motivo': f'Módulo para tela {tela} não encontrado'
                })
            
            # Verificar permissão
            permissao_existe = PermissaoModulo.objects.using(banco).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_modu=modulo,
                perm_ativ=True
            ).exists()
            
            return Response({
                'permitido': permissao_existe,
                'tela': tela,
                'operacao': operacao,
                'modulo': modulo.modu_nome
            })
            
        except Exception as e:
            logger.error(f"Erro ao verificar permissão: {e}")
            return Response(
                {'permitido': False, 'erro': 'Erro ao verificar permissão'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



