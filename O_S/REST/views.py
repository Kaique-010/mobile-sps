from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework import status, filters
from rest_framework.response import Response
from django.http import HttpResponse
from core.impressoes.documentos.os import OrdemServicoPrinter
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from ..filters.os import OsFilter, OrdemServicoGeralFilter
from django.db import transaction, IntegrityError
from django.db.models import Max, OuterRef, Subquery, DecimalField, Value as V
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from ..utils import get_next_item_number_sequence, get_next_service_id, get_next_global_peca_item_id, get_next_global_serv_item_id, get_next_global_os_hora_item_id
from listacasamento.utils import get_next_item_number
from ..permissions import PodeVerOrdemDoSetor
from ..models import Os, PecasOs, ServicosOs, OsHora
from .serializers import (
                            OsSerializer, PecasOsSerializer, 
                            ServicosOsSerializer, OsHoraSerializer)
from django.db import models
from django.db.models import Prefetch
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.dominio_handler import tratar_erro, tratar_sucesso
from core.excecoes import ErroDominio

import logging
logger = logging.getLogger(__name__)
import base64


class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):

    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise ErroDominio("Banco de dados não encontrado.", codigo="banco_nao_encontrado")
        return banco

    def get_queryset(self):
        return super().get_queryset().using(self.get_banco())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    @transaction.atomic(using='default')
    def create(self, request, *args, **kwargs):
        try:
            banco = self.get_banco()
            data = request.data
            is_many = isinstance(data, list)
            serializer = self.get_serializer(data=data, many=is_many)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic(using=banco):
                serializer.save()
            return tratar_sucesso(serializer.data, status_code=status.HTTP_201_CREATED)
        except Exception as e:
            return tratar_erro(e)

    def update(self, request, *args, **kwargs):
        try:
            banco = self.get_banco()
            partial = kwargs.pop('partial', False)
            instance = self.get_object()        
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic(using=banco):
                serializer.save()
            return tratar_sucesso(serializer.data)
        except Exception as e:
            return tratar_erro(e)


class OsViewSet(BaseMultiDBModelViewSet):
    permission_classes = [PodeVerOrdemDoSetor]
    serializer_class = OsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = OsFilter
    ordering_fields = ['os_os']
    search_fields = ['os_prob_rela', 'os_obse']
   
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    def get_queryset(self):
        banco = self.get_banco()
        empresa = (
            self.request.query_params.get('os_empr') or 
            self.request.query_params.get('empresa_id') or 
            self.request.query_params.get('empr')
        )
        filial = (
            self.request.query_params.get('os_fili') or 
            self.request.query_params.get('filial_id') or 
            self.request.query_params.get('fili')
        )
        qs = Os.objects.using(banco).filter(os_empr=empresa, os_fili=filial)

        return qs.order_by('-os_os')
    
    def get_object(self):
        banco = self.get_banco()
        empresa = (
            self.request.query_params.get('os_empr') or 
            self.request.query_params.get('empresa_id') or 
            self.request.query_params.get('empr')
        )
        filial = (
            self.request.query_params.get('os_fili') or 
            self.request.query_params.get('filial_id') or 
            self.request.query_params.get('fili')
        )
        
        pk = self.kwargs['pk']
        
        # Verifica se o PK é um UUID/ID Offline (string longa ou com hifens)
        # Isso permite buscar a OS pelo ID gerado offline caso o app ainda não tenha o ID oficial
        is_uuid = str(pk) and (len(str(pk)) > 20 or '-' in str(pk))
        
        if is_uuid:
            logger.info(f"Buscando OS por UUID/Auto={pk} no banco {banco}")
            qs = Os.objects.using(banco).filter(os_auto=pk)
            if empresa and filial:
                qs = qs.filter(os_empr=empresa, os_fili=filial)
            
            obj = qs.first()
            if obj:
                self.check_object_permissions(self.request, obj)
                return obj
            # Se parece UUID mas não achou, retorna erro específico ou deixa cair no 404
            raise ErroDominio("Ordem de Serviço não encontrada pelo ID offline fornecido.", codigo="os_nao_encontrada_uuid")

        try:
            logger.info(f"Buscando OS com pk={pk} e empresa={empresa} filial={filial} no banco {banco}")
            
            # Se não passar empresa/filial, tenta buscar só por PK (comportamento antigo), 
            # mas corre risco de MultipleObjectsReturned
            if not empresa or not filial:
                obj = Os.objects.using(banco).get(pk=pk)
            else:
                obj = Os.objects.using(banco).get(
                    pk=pk,
                    os_empr=empresa, 
                    os_fili=filial
                )
            
            self.check_object_permissions(self.request, obj)
            return obj
            
        except Os.DoesNotExist:
            raise ErroDominio("Ordem de Serviço não encontrada.", codigo="os_nao_encontrada")
        except Os.MultipleObjectsReturned:
            raise ErroDominio(
                "Múltiplas Ordens de Serviço encontradas com o mesmo código. Informe a empresa e filial.", 
                codigo="os_multiplas_encontradas"
            )
        except ValueError:
             raise ErroDominio("ID da ordem inválido.", codigo="id_invalido")
        
    @action(detail=True, methods=['post'])
    def finalizar_os(self, request, pk=None):
        """Endpoint para finalizar uma OS com validações"""
        try:
            os_instance = self.get_object()
            
            # Validações de negócio
            if os_instance.os_stat_os == 2:
                raise ErroDominio('OS já finalizada', codigo="os_ja_finalizada")
            
            # Verificar se tem peças ou serviços
            banco = self.get_banco()
            tem_pecas = PecasOs.objects.using(banco).filter(
                peca_os=os_instance.os_os
            ).exists()
            tem_servicos = ServicosOs.objects.using(banco).filter(
                serv_os=os_instance.os_os
            ).exists()
            
            if not tem_pecas and not tem_servicos:
                raise ErroDominio('OS deve ter pelo menos uma peça ou serviço', codigo="os_vazia")
            
            with transaction.atomic(using=banco):
                from O_S.services.os_service import OsService
                OsService.finalizar_os(banco, os_instance)
            
            return tratar_sucesso(mensagem='OS finalizada com sucesso')
        except Exception as e:
            return tratar_erro(e)

    def get_next_ordem_numero(self, empre, fili):
        banco = self.get_banco()
        ultimo = Os.objects.using(banco).filter(os_empr=empre, os_fili=fili).aggregate(Max('os_os'))['os_os__max']
        return (ultimo or 0) + 1
    
    

    def create(self, validated_data):
        # Override create to use OsService logic is not possible directly here because 
        # BaseMultiDBModelViewSet.create calls serializer.save()
        # We need to override create in OsViewSet, not here.
        pass

    def create(self, request, *args, **kwargs):
        try:
            banco = self.get_banco()
            base_data = request.data.copy()
            #Se não for fornecido, definir como 1
            if not base_data.get('os_seto'):
                base_data['os_seto'] = 1

            # Checar offline o uuid enviado pelo front e persistir no os_auto
            local_os_id = base_data.get('os_auto')
            os_id = request.data.get('os_os')
            
            logger.info(f"Recebendo requisição de criação de OS. os_auto={local_os_id}, os_os={os_id}, user={request.user.pk if request.user else 'anon'}")

            if os_id and isinstance(os_id, str) and (len(os_id) > 20 or '-' in os_id):
                local_os_id = os_id
                base_data['os_auto'] = local_os_id
                base_data['os_os'] = "0"
            elif not os_id:
                 base_data['os_os'] = "0"
            base_data['os_stat_os'] = 0
            
            #Usuário responsável pela OS
            if request.user and request.user.pk:
                base_data['os_usua_aber'] = request.user.pk

            empresa = base_data.get('os_empr') or base_data.get('empr')
            filial = base_data.get('os_fili') or base_data.get('fili')
            if not empresa or not filial:
                raise ErroDominio("Empresa e Filial são obrigatórios.", codigo="dados_obrigatorios")
            
            # IDEMPOTENCY CHECK: Se já existe uma OS com esse UUID, retorna ela sem criar nova
            if local_os_id:
                existing = Os.objects.using(banco).filter(
                    os_empr=empresa, 
                    os_fili=filial, 
                    os_auto=local_os_id
                ).first()
                if existing:
                    logger.info(f"OS {existing.os_os} já existe (UUID={local_os_id}). Retornando existente para evitar duplicação.")
                    try:
                        response_serializer = self.get_serializer(existing)
                        response_data = response_serializer.data
                        response_data['local_os_id'] = local_os_id
                        response_data['remote_os_id'] = existing.os_os
                        
                        # Tentar reconstruir os mapeamentos de IDs
                        try:
                            # Serializa os dados de entrada para ter acesso às listas de itens
                            # Re-validamos apenas para obter os dados limpos, sem salvar
                            serializer_check = self.get_serializer(data=base_data)
                            if serializer_check.is_valid():
                                val_data = serializer_check.validated_data
                                pecas_data = val_data.get('pecas', [])
                                servicos_data = val_data.get('servicos', [])
                                horas_data = val_data.get('horas', [])
                                
                                id_mappings = {
                                    'pecas_ids': [],
                                    'servicos_ids': [],
                                    'horas_ids': []
                                }
                                
                                # Reconstruir mapeamento de Peças
                                existing_pecas = PecasOs.objects.using(banco).filter(
                                    peca_empr=existing.os_empr,
                                    peca_fili=existing.os_fili,
                                    peca_os=existing.os_os
                                ).order_by('peca_item')
                                
                                for idx, item_data in enumerate(pecas_data):
                                    if idx < len(existing_pecas):
                                        local_id = item_data.get('peca_item')
                                        if local_id:
                                            id_mappings['pecas_ids'].append({
                                                'local_id': local_id, 
                                                'remote_id': existing_pecas[idx].peca_item
                                            })
                                            
                                # Reconstruir mapeamento de Serviços
                                existing_servicos = ServicosOs.objects.using(banco).filter(
                                    serv_empr=existing.os_empr,
                                    serv_fili=existing.os_fili,
                                    serv_os=existing.os_os
                                ).order_by('serv_item')
                                
                                for idx, item_data in enumerate(servicos_data):
                                    if idx < len(existing_servicos):
                                        local_id = item_data.get('serv_item')
                                        if local_id:
                                            id_mappings['servicos_ids'].append({
                                                'local_id': local_id, 
                                                'remote_id': existing_servicos[idx].serv_item
                                            })
                                            
                                # Reconstruir mapeamento de Horas
                                existing_horas = OsHora.objects.using(banco).filter(
                                    os_hora_empr=existing.os_empr,
                                    os_hora_fili=existing.os_fili,
                                    os_hora_os=existing.os_os
                                ).order_by('os_hora_item')
                                
                                for idx, item_data in enumerate(horas_data):
                                    if idx < len(existing_horas):
                                        local_id = item_data.get('os_hora_item')
                                        if local_id:
                                            id_mappings['horas_ids'].append({
                                                'local_id': local_id, 
                                                'remote_id': existing_horas[idx].os_hora_item
                                            })
                                
                                response_data.update(id_mappings)
                        except Exception as map_err:
                            logger.error(f"Erro ao reconstruir mapeamentos para OS {existing.os_os}: {map_err}")

                    except Exception as e:
                        logger.error(f"Erro ao serializar OS existente {existing.os_os}: {e}")
                        response_data = {
                            "os_os": existing.os_os,
                            "os_empr": existing.os_empr,
                            "os_fili": existing.os_fili,
                            "local_os_id": local_os_id,
                            "remote_os_id": existing.os_os,
                            "warning": "Erro na serialização da OS existente."
                        }
                    return tratar_sucesso(response_data, status_code=status.HTTP_200_OK)

            base_data['os_prof_aber'] = request.user.pk if request.user else None
            serializer = self.get_serializer(data=base_data)
            if not serializer.is_valid():
                logger.error(f"Erro de validação ao criar OS: {serializer.errors}")
                serializer.is_valid(raise_exception=True)
            
            validated_data = serializer.validated_data
            pecas_data = validated_data.pop('pecas', [])
            servicos_data = validated_data.pop('servicos', [])
            horas_data = validated_data.pop('horas', []) 
            os_data = validated_data
            # Deixar o Service calcular o ID dentro da transação para garantir atomicidade
            # e evitar race conditions na verificação de idempotência
            if 'os_os' in os_data:
                del os_data['os_os']
            
            # Garantir que os_auto esteja presente para verificação de idempotência no Service
            if local_os_id and 'os_auto' not in os_data:
                    os_data['os_auto'] = local_os_id

            from O_S.services.os_service import OsService
            instance = OsService.create_os(banco, os_data, pecas_data, servicos_data, horas_data)
                
            logger.info(
                f"O.S. {instance.os_os} aberta por user {request.user.pk if request.user else 'anon'}"
            )
            
            # Re-serialize instance for response
            try:
                response_serializer = self.get_serializer(instance)
                response_data = response_serializer.data
                
                if hasattr(instance, 'id_mappings'):
                    response_data.update(instance.id_mappings)

                if local_os_id:
                    response_data['local_os_id'] = local_os_id
                    response_data['remote_os_id'] = instance.os_os
            except Exception as e:
                logger.error(f"Erro ao serializar resposta da OS {instance.os_os}: {e}")
                # Fallback response para evitar retries do cliente se a OS já foi criada
                response_data = {
                    "os_os": instance.os_os,
                    "os_empr": instance.os_empr,
                    "os_fili": instance.os_fili,
                    "local_os_id": local_os_id if local_os_id else None,
                    "remote_os_id": instance.os_os,
                    "warning": "Erro na serialização completa dos dados. OS criada com sucesso."
                }
            
            return tratar_sucesso(response_data, status_code=status.HTTP_201_CREATED)
        except Exception as e:
            return tratar_erro(e)

    def update(self, request, *args, **kwargs):
        try:
            banco = self.get_banco()
            instance = self.get_object()
            
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True)
            
            validated_data = serializer.validated_data
            pecas_data = validated_data.pop('pecas', [])
            servicos_data = validated_data.pop('servicos', [])
            horas_data = validated_data.pop('horas', [])
            # os_updates = remaining validated_data
            
            from O_S.services.os_service import OsService
            # Note: update_os expects (banco, ordem, os_updates, pecas_data, servicos_data, horas_data)
            instance = OsService.update_os(banco, instance, validated_data, pecas_data, servicos_data, horas_data)
            
            response_serializer = self.get_serializer(instance)
            return tratar_sucesso(response_serializer.data)
        except Exception as e:
            return tratar_erro(e)

    """
    Endpoint para cancelar uma Ordem de Serviço, cancelando e alterando o Status e voltando os 
    itens para o estoque.
    """
    def destroy(self, request, *args, **kwargs):
        banco = self.get_banco()
        ordem = self.get_object()

        try:
            with transaction.atomic(using=banco):
                # Verifica se já está cancelada para evitar duplicação de estorno
                if ordem.os_stat_os == 3:
                    return tratar_sucesso(mensagem='OS já estava cancelada.')

                from O_S.services.os_service import OsService
                OsService.cancelar_os(banco, ordem)

            return tratar_sucesso(
                mensagem='OS cancelada e itens retornaram ao estoque.'
            )

        except Exception as e:
            return tratar_erro(e)
        
            
    @action(
        detail=True, 
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def atualizar_total(self, request, pk=None, slug=None):
        """
        Endpoint para atualizar o total da ordem de serviço.
        """
        try:
            banco = self.get_banco()
            ordem = self.get_object()
            
            with transaction.atomic(using=banco):
                from O_S.services.os_service import OsService
                OsService.calcular_total(banco, ordem)
            
            serializer = self.get_serializer(ordem)
            return tratar_sucesso(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao atualizar total da ordem {pk}: {str(e)}")
            return tratar_erro(e)
    
    @action(detail=False, methods=['patch'], url_path='patch')
    def patch_ordem(self, request, slug=None):
        try:
            banco = self.get_banco()
            os_pk = request.data.get('os_os') or request.data.get('pk')
            if not os_pk:
                raise ErroDominio('os_os obrigatório', codigo="dados_obrigatorios")
            try:
                instance = Os.objects.using(banco).get(pk=os_pk)
            except Os.DoesNotExist:
                raise ErroDominio('Ordem de Serviço não encontrada.', codigo="os_nao_encontrada")
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic(using=banco):
                serializer.save()
            return tratar_sucesso(serializer.data)
        except Exception as e:
            return tratar_erro(e)
    
    
    @action(detail=True, methods=['get'])
    def imprimir(self, request, pk=None, slug=None):
        """
        Endpoint para imprimir uma Ordem de Serviço em PDF.
        """
        try:
           
            # Importa models necessários
            from Entidades.models import Entidades
            from Licencas.models import Filiais
            from ..models import PecasOs, ServicosOs, OsHora
            
            # Obtém nome do banco (multi-tenant)
            banco = self.get_banco()
            
            # Obtém a Ordem de Serviço específica
            os = self.get_object()

            # ---------------------------------------------------------------
            # Busca entidades relacionadas
            # ---------------------------------------------------------------
            
            # Cliente da OS
            cliente = Entidades.objects.using(banco).filter(
                enti_clie=os.os_clie
            ).first()
            
            # Filial/Empresa que está executando
            filial = Filiais.objects.using(banco).filter(
                empr_empr=os.os_empr,
                empr_codi=os.os_fili
            ).first()
            
            # Solicitante (quem pediu o serviço)
            solicitante = Entidades.objects.using(banco).filter(
                enti_clie=os.os_clie
            ).first()
            
            # Responsável em campo (quem executou)
            responsavel_campo = None
            if getattr(os, 'os_resp', None):
                responsavel_campo = Entidades.objects.using(banco).filter(
                    enti_clie=os.os_resp
                ).first()

            # ---------------------------------------------------------------
            # Busca itens relacionados
            # ---------------------------------------------------------------
            
            # Peças utilizadas
            pecas = PecasOs.objects.using(banco).filter(
                peca_empr=os.os_empr,
                peca_fili=os.os_fili,
                peca_os=os.os_os
            )
            
            # Serviços executados
            servicos = ServicosOs.objects.using(banco).filter(
                serv_empr=os.os_empr,
                serv_fili=os.os_fili,
                serv_os=os.os_os
            )
            
            # Horas trabalhadas (ordenadas por item)
            horas = OsHora.objects.using(banco).filter(
                os_hora_empr=os.os_empr,
                os_hora_fili=os.os_fili,
                os_hora_os=os.os_os
            ).order_by('os_hora_item')

            # ===============================================================
            # 2. PROCESSA ASSINATURAS
            # ===============================================================
            
            def process_signature(signature_data):
                """
                Processa assinatura em diferentes formatos.
                """
                if not signature_data:
                    return None
                
                try:
                    # Se for memoryview, converte para bytes
                    if isinstance(signature_data, memoryview):
                        return base64.b64encode(signature_data.tobytes()).decode('utf-8')
                    
                    # Se for bytes direto
                    if isinstance(signature_data, bytes):
                        return base64.b64encode(signature_data).decode('utf-8')
                    
                    # Se já for string, retorna como está
                    if isinstance(signature_data, str):
                        return signature_data
                except Exception:
                    return None
                
                return None
            
            # Monta dicionário de assinaturas
            assinaturas = {}
            
            # Assinatura do cliente (se existir)
            assin_cliente = process_signature(getattr(os, 'os_assi_clie', None))
            if assin_cliente:
                assinaturas['Assinatura do Cliente'] = assin_cliente
            
            # Assinatura do operador (se existir)
            assin_operador = process_signature(getattr(os, 'os_assi_oper', None))
            if assin_operador:
                assinaturas['Assinatura do Operador'] = assin_operador
            
            # Permite assinaturas adicionais via request (opcional)
            if request.data.get('assinaturas'):
                assinaturas.update(request.data.get('assinaturas', {}))

            # ===============================================================
            # 3. CRIA INSTÂNCIA DO PRINTER
            # ===============================================================
            
            printer = OrdemServicoPrinter(
                filial=filial or os.os_fili,  # Fallback para código se não achar objeto
                documento=os.os_os,            # Número da OS
                cliente=cliente,               # Objeto cliente
                solicitante=solicitante,       # Quem solicitou
                responsavel_campo=responsavel_campo,  # Quem executou
                modelo=os,                     # Objeto principal da OS
                itens=pecas,                   # QuerySet de peças
                servicos=servicos,             # QuerySet de serviços
                horas=horas,                   # QuerySet de horas
                assinaturas=assinaturas,       # Dict de assinaturas processadas
            )

            # ===============================================================
            # 4. GERA O PDF
            # ===============================================================
            
            # Chama render() que executa toda a lógica de geração
            pdf_buffer = printer.render()

            # ===============================================================
            # 5. RETORNA RESPOSTA HTTP
            # ===============================================================
            
            # Cria resposta HTTP com o PDF
            response = HttpResponse(
                pdf_buffer.getvalue(),  # Obtém bytes do buffer
                content_type='application/pdf'
            )
            
            # Define visualização inline no navegador (não download)
            # Para forçar download, use 'attachment' ao invés de 'inline'
            response['Content-Disposition'] = f'inline; filename="os_{os.os_os}.pdf"'
            
            return response
        except Exception as e:
            # Em caso de erro na geração do PDF, retornamos JSON com erro
            return tratar_erro(e)
    
    
class PecasOsViewSet(BaseMultiDBModelViewSet):
    serializer_class = PecasOsSerializer
    parser_classes = [JSONParser]

    def atualizar_total_ordem(self, peca_empr, peca_fili, peca_os):
        banco = self.get_banco()
        try:
            ordem = Os.objects.using(banco).get(
                os_empr=peca_empr,
                os_fili=peca_fili,
                os_os=peca_os
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Os.DoesNotExist:
            logger.error(f"Ordem não encontrada para recalcular: {peca_os}")

    def get_queryset(self):
        banco = self.get_banco()

        peca_empr = self.request.query_params.get('peca_empr')
        peca_fili = self.request.query_params.get('peca_fili')
        peca_os = self.request.query_params.get('peca_os')

        if not all([peca_empr, peca_fili, peca_os]):
            logger.warning("Query sem parâmetros (peca_empr, peca_fili, peca_os). Retornando vazio.")
            return PecasOs.objects.none()

        qs = PecasOs.objects.using(banco).filter(
            peca_empr=peca_empr,
            peca_fili=peca_fili,
            peca_os=peca_os
        )

        return qs.order_by('peca_item')

    def get_object(self):
        banco = self.get_banco()

        peca_item = self.kwargs.get('pk')
        peca_os = self.request.query_params.get("peca_os")
        peca_empr = self.request.query_params.get("peca_empr")
        peca_fili = self.request.query_params.get("peca_fili")

        if not all([peca_os, peca_empr, peca_fili, peca_item]):
            raise ErroDominio("Faltam parâmetros: peca_item, peca_os, peca_empr, peca_fili.", codigo="parametros_invalidos")

        try:
            return PecasOs.objects.using(banco).get(
                peca_item=peca_item,
                peca_os=peca_os,
                peca_empr=peca_empr,
                peca_fili=peca_fili
            )
        except PecasOs.DoesNotExist:
            raise ErroDominio("Peça não encontrada.", codigo="peca_nao_encontrada")
        except PecasOs.MultipleObjectsReturned:
            raise ErroDominio("Chave composta retornou múltiplos registros.", codigo="multiplos_registros")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['banco'] = self.get_banco()
        return ctx



    # CREATE único e correto
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()

        try:
            is_many = isinstance(request.data, list)
            serializer = self.get_serializer(data=request.data, many=is_many)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic(using=banco):
                objs = serializer.save()

            # recalcula total da OS
            if is_many:
                exemplo = request.data[0]
            else:
                exemplo = request.data

            self.atualizar_total_ordem(
                exemplo.get('peca_empr'),
                exemplo.get('peca_fili'),
                exemplo.get('peca_os')
            )

            return tratar_sucesso(serializer.data, status_code=status.HTTP_201_CREATED)

        except Exception as e:
            return tratar_erro(e)

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            # Como super().update agora chama tratar_sucesso, response.data pode ter mudado estrutura
            # Mas response.status_code deve ser 200
            if response.status_code == 200:
                instance = self.get_object()
                self.atualizar_total_ordem(
                    instance.peca_empr, instance.peca_fili, instance.peca_os
                )
            return response
        except Exception as e:
            return tratar_erro(e)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            empr, fili, orde = instance.peca_empr, instance.peca_fili, instance.peca_os
            response = super().destroy(request, *args, **kwargs)

            if response.status_code == 204:
                self.atualizar_total_ordem(empr, fili, orde)

            return response
        except Exception as e:
            return tratar_erro(e)

    # atualização em lote padronizada
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = self.get_banco()
        data = request.data

        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):

                # ADICIONAR
                for item in adicionar:
                    campos_obrig = ['peca_os', 'peca_empr', 'peca_fili', 'peca_prod']
                    faltando = [c for c in campos_obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Faltam campos: {', '.join(faltando)}")

                    # peca_item é PK globalmente; garantir ID único mesmo entre ordens distintas
                    item['peca_item'] = get_next_global_peca_item_id(banco)

                    s = PecasOsSerializer(data=item, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    obj = s.save()

                    resposta['adicionados'].append(
                        PecasOsSerializer(obj, context={'banco': banco}).data
                    )

                # EDITAR
                for item in editar:
                    required = ['peca_item', 'peca_os', 'peca_empr', 'peca_fili']
                    if not all(k in item for k in required):
                        raise ValidationError("Campos obrigatórios para edição faltando.")

                    try:
                        obj = PecasOs.objects.using(banco).get(
                            peca_item=item['peca_item'],
                            peca_os=item['peca_os'],
                            peca_empr=item['peca_empr'],
                            peca_fili=item['peca_fili']
                        )
                    except PecasOs.DoesNotExist:
                        continue

                    s = PecasOsSerializer(obj, data=item, partial=True, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    s.save()
                    resposta['editados'].append(s.data)

                # REMOVER
                for item in remover:
                    required = ['peca_item', 'peca_os', 'peca_empr', 'peca_fili']
                    if not all(k in item for k in required):
                        raise ValidationError("Campos obrigatórios para remover faltando.")

                    PecasOs.objects.using(banco).filter(
                        peca_item=item['peca_item'],
                        peca_os=item['peca_os'],
                        peca_empr=item['peca_empr'],
                        peca_fili=item['peca_fili']
                    ).delete()

                    resposta['removidos'].append(item['peca_item'])

            return tratar_sucesso(resposta)

        except Exception as e:
            return tratar_erro(e)



class ServicosOsViewSet(BaseMultiDBModelViewSet):
    serializer_class = ServicosOsSerializer
    parser_classes = [JSONParser]

    # ---- UTILIDADES ----
    def atualizar_total_ordem(self, serv_empr, serv_fili, serv_os):
        banco = self.get_banco()
        try:
            ordem = Os.objects.using(banco).get(
                os_empr=serv_empr,
                os_fili=serv_fili,
                os_os=serv_os
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Os.DoesNotExist:
            logger.error(f"Ordem de serviço não encontrada para recalcular: {serv_os}")

    # ---- QUERYSET ----
    def get_queryset(self):
        banco = self.get_banco()

        serv_empr = self.request.query_params.get("serv_empr")
        serv_fili = self.request.query_params.get("serv_fili")
        serv_os = self.request.query_params.get("serv_os")

        if not all([serv_empr, serv_fili, serv_os]):
            logger.warning("Parâmetros obrigatórios faltando (serv_empr, serv_fili, serv_os)")
            return ServicosOs.objects.none()

        qs = ServicosOs.objects.using(banco).filter(
            serv_empr=serv_empr,
            serv_fili=serv_fili,
            serv_os=serv_os
        )

        return qs.order_by("serv_item")

    # ---- GET OBJECT ----
    def get_object(self):
        banco = self.get_banco()

        serv_item = self.kwargs.get("pk")
        serv_os = self.request.query_params.get("serv_os")
        serv_empr = self.request.query_params.get("serv_empr")
        serv_fili = self.request.query_params.get("serv_fili")

        if not all([serv_item, serv_os, serv_empr, serv_fili]):
            raise ErroDominio("Campos serv_os, serv_empr, serv_fili e pk (serv_item) são obrigatórios.", codigo="dados_obrigatorios")

        try:
            return self.get_queryset().get(
                serv_item=serv_item,
                serv_os=serv_os,
                serv_empr=serv_empr,
                serv_fili=serv_fili
            )
        except ServicosOs.DoesNotExist:
            raise ErroDominio("Serviço não encontrado na lista especificada.", codigo="servico_nao_encontrado")
        except ServicosOs.MultipleObjectsReturned:
            raise ErroDominio("Mais de um serviço encontrado com essa chave composta.", codigo="multiplos_registros")

    # ---- CONTEXT ----
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    # ---- CREATE ----
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        try:
            is_many = isinstance(request.data, list)
            data_in = request.data
            data_copy = [d.copy() for d in data_in] if is_many else data_in.copy()
            if is_many:
                for item in data_copy:
                    if not item.get('serv_item'):
                        item['serv_item'] = get_next_global_serv_item_id(banco)
            else:
                if not data_copy.get('serv_item'):
                    data_copy['serv_item'] = get_next_global_serv_item_id(banco)

            serializer = self.get_serializer(data=data_copy, many=is_many)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic(using=banco):
                objs = serializer.save()

            exemplo = data_copy[0] if is_many else data_copy

            self.atualizar_total_ordem(
                exemplo.get('serv_empr'),
                exemplo.get('serv_fili'),
                exemplo.get('serv_os')
            )

            return tratar_sucesso(serializer.data, status_code=status.HTTP_201_CREATED)

        except Exception as e:
            return tratar_erro(e)

    # ---- UPDATE ----
    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            if response.status_code == 200:
                instance = self.get_object()
                self.atualizar_total_ordem(
                    instance.serv_empr,
                    instance.serv_fili,
                    instance.serv_os
                )
            return response
        except Exception as e:
            return tratar_erro(e)

    # ---- DELETE ----
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            empr, fili, orde = instance.serv_empr, instance.serv_fili, instance.serv_os
            response = super().destroy(request, *args, **kwargs)

            if response.status_code == 204:
                self.atualizar_total_ordem(empr, fili, orde)

            return response
        except Exception as e:
            return tratar_erro(e)

    # ---- UPDATE LISTA (LOTE) ----
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = self.get_banco()
        data = request.data

        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        def normalize_item(item, prefix):
            if not isinstance(item, dict):
                return
            # Normaliza chaves comuns
            if not item.get(f'{prefix}_empr'):
                item[f'{prefix}_empr'] = item.get('empr') or item.get('os_empr')
            if not item.get(f'{prefix}_fili'):
                item[f'{prefix}_fili'] = item.get('fili') or item.get('os_fili')
            if not item.get(f'{prefix}_os'):
                item[f'{prefix}_os'] = item.get('os') or item.get('os_os')
            if not item.get(f'{prefix}_prod'):
                item[f'{prefix}_prod'] = item.get('prod') or item.get('codigo')
            if not item.get(f'{prefix}_stat'):
                item[f'{prefix}_stat'] = item.get('status') or item.get('stat')

        try:
            with transaction.atomic(using=banco):

                # ADICIONAR
                for item in adicionar:
                    if not isinstance(item, dict):
                        logger.warning(f"Item inválido em adicionar: {item}")
                        continue

                    normalize_item(item, 'serv')
                    obrig = ['serv_os', 'serv_empr', 'serv_fili', 'serv_prod']
                    faltando = [c for c in obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Faltam campos para adicionar: {', '.join(faltando)}")

                    item['serv_item'] = get_next_global_serv_item_id(banco)

                    s = ServicosOsSerializer(data=item, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    obj = s.save()

                    resposta['adicionados'].append(
                        ServicosOsSerializer(obj, context={'banco': banco}).data
                    )

                # EDITAR
                for item in editar:
                    if not isinstance(item, dict):
                        logger.warning(f"Item inválido em editar: {item}")
                        continue

                    normalize_item(item, 'serv')
                    obrig = ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']
                    faltando = [c for c in obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Campos obrigatórios para edição faltando: {', '.join(faltando)}")

                    try:
                        obj = ServicosOs.objects.using(banco).get(
                            serv_item=item['serv_item'],
                            serv_os=item['serv_os'],
                            serv_empr=item['serv_empr'],
                            serv_fili=item['serv_fili']
                        )
                    except ServicosOs.DoesNotExist:
                        continue

                    s = ServicosOsSerializer(obj, data=item, partial=True, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    s.save()
                    resposta['editados'].append(s.data)

                # REMOVER
                for item in remover:
                    # Suporte para remoção apenas pelo ID (int ou str)
                    if isinstance(item, (int, str)):
                        try:
                            ServicosOs.objects.using(banco).filter(serv_item=item).delete()
                            resposta['removidos'].append(item)
                        except Exception as e:
                            logger.error(f"Erro ao remover item {item}: {e}")
                        continue

                    if not isinstance(item, dict):
                        logger.warning(f"Item inválido em remover: {item}")
                        continue

                    normalize_item(item, 'serv')
                    obrig = ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']
                    faltando = [c for c in obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Campos obrigatórios para remover faltando: {', '.join(faltando)}")

                    ServicosOs.objects.using(banco).filter(
                        serv_item=item['serv_item'],
                        serv_os=item['serv_os'],
                        serv_empr=item['serv_empr'],
                        serv_fili=item['serv_fili']
                    ).delete()

                    resposta['removidos'].append(item['serv_item'])

            return tratar_sucesso(resposta)

        except Exception as e:
            return tratar_erro(e)



class OsHoraViewSet(BaseMultiDBModelViewSet):
    serializer_class = OsHoraSerializer
    parser_classes = [JSONParser]
    lookup_field = 'os_hora_item'

    def get_queryset(self):
        banco = self.get_banco()
        
        os_hora_empr = self.request.query_params.get('os_hora_empr')
        os_hora_fili = self.request.query_params.get('os_hora_fili')
        os_hora_os = self.request.query_params.get('os_hora_os')
        
        if not all([os_hora_empr, os_hora_fili, os_hora_os]):
            logger.warning("Parâmetros obrigatórios faltando para OsHora")
            return OsHora.objects.none()
        
        return OsHora.objects.using(banco).filter(
            os_hora_empr=os_hora_empr,
            os_hora_fili=os_hora_fili,
            os_hora_os=os_hora_os
        ).order_by('os_hora_data', 'os_hora_item')
    
    def retrieve(self, request, *args, **kwargs):
        try:
            obj = self.get_object()
            serializer = self.get_serializer(obj)
            return tratar_sucesso(serializer.data)
        except Exception as e:
            return tratar_erro(e)
    
    def get_object(self):
        banco = self.get_banco()
        
        os_hora_item = self.kwargs.get('pk') or self.kwargs.get('os_hora_item')
        
        # Tenta pegar da query string, se não tiver, tenta do body (request.data)
        os_hora_os = self.request.query_params.get('os_hora_os') or self.request.data.get('os_hora_os')
        os_hora_empr = self.request.query_params.get('os_hora_empr') or self.request.data.get('os_hora_empr')
        os_hora_fili = self.request.query_params.get('os_hora_fili') or self.request.data.get('os_hora_fili')
        
        if os_hora_item:
            # Se temos o ID do item, tentamos buscar por ele
            # Se vierem outros parâmetros, usamos para garantir integridade (filtro adicional)
            filter_kwargs = {'os_hora_item': os_hora_item}
            if os_hora_os:
                filter_kwargs['os_hora_os'] = os_hora_os
            if os_hora_empr:
                filter_kwargs['os_hora_empr'] = os_hora_empr
            if os_hora_fili:
                filter_kwargs['os_hora_fili'] = os_hora_fili
            
            try:
                return OsHora.objects.using(banco).get(**filter_kwargs)
            except OsHora.DoesNotExist:
                raise ErroDominio("Registro de horas não encontrado", codigo="hora_nao_encontrada")
            except OsHora.MultipleObjectsReturned:
                raise ErroDominio("Múltiplos registros encontrados. Forneça os_hora_os, os_hora_empr e os_hora_fili para identificar unicamente.", codigo="multiplos_registros")

        if not all([os_hora_item, os_hora_os, os_hora_empr, os_hora_fili]):
            logger.error(f"Parâmetros faltando OsHoraViewSet.get_object: kwargs={self.kwargs}, query={self.request.query_params}")
            raise ErroDominio("Parâmetros obrigatórios faltando", codigo="dados_obrigatorios")
        
        try:
            return OsHora.objects.using(banco).get(
                os_hora_item=os_hora_item,
                os_hora_os=os_hora_os,
                os_hora_empr=os_hora_empr,
                os_hora_fili=os_hora_fili
            )
        except OsHora.DoesNotExist:
            raise ErroDominio("Registro de horas não encontrado", codigo="hora_nao_encontrada")
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        
        try:
            is_many = isinstance(request.data, list)
            data_copy = request.data.copy() if not is_many else [item.copy() for item in request.data]
            
            # Gerar os_hora_item automaticamente (global)
            if is_many:
                for item in data_copy:
                    if not item.get('os_hora_item'):
                        item['os_hora_item'] = get_next_global_os_hora_item_id(banco)
            else:
                if not data_copy.get('os_hora_item'):
                    data_copy['os_hora_item'] = get_next_global_os_hora_item_id(banco)
            
            serializer = self.get_serializer(data=data_copy, many=is_many)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic(using=banco):
                serializer.save()
            
            return tratar_sucesso(serializer.data, status_code=status.HTTP_201_CREATED)
        
        except Exception as e:
            return tratar_erro(e)
    
    def _get_next_item_number(self, banco, os_os, os_empr, os_fili):
        """Gera próximo número de item"""
        ultimo = OsHora.objects.using(banco).filter(
            os_hora_os=os_os,
            os_hora_empr=os_empr,
            os_hora_fili=os_fili
        ).aggregate(Max('os_hora_item'))['os_hora_item__max']
        return (ultimo or 0) + 1
    
    @action(detail=False, methods=['get'], url_path='total-horas')
    def total_horas(self, request, slug=None):
        """Retorna total de horas trabalhadas na OS"""
        try:
            banco = self.get_banco()
            
            os_hora_os = request.query_params.get('os_hora_os')
            os_hora_empr = request.query_params.get('os_hora_empr')
            os_hora_fili = request.query_params.get('os_hora_fili')
            
            if not all([os_hora_os, os_hora_empr, os_hora_fili]):
                raise ErroDominio('Parâmetros obrigatórios faltando', codigo="dados_obrigatorios")
            
            registros = OsHora.objects.using(banco).filter(
                os_hora_os=os_hora_os,
                os_hora_empr=os_hora_empr,
                os_hora_fili=os_hora_fili
            )
            
            total = 0.0
            for registro in registros:
                serializer = OsHoraSerializer(registro, context={'banco': banco})
                total += serializer.data.get('total_horas', 0)
            
            return tratar_sucesso({
                'total_horas': round(total, 2),
                'total_registros': registros.count()
            })
        except Exception as e:
            return tratar_erro(e)
    
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        """Atualização em lote de registros de horas"""
        banco = self.get_banco()
        data = request.data

        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):

                # ADICIONAR
                for item in adicionar:
                    obrig = ['os_hora_os', 'os_hora_empr', 'os_hora_fili', 'os_hora_data']
                    faltando = [c for c in obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Faltam campos: {', '.join(faltando)}")

                    if not item.get('os_hora_item'):
                        item['os_hora_item'] = get_next_global_os_hora_item_id(banco)

                    s = OsHoraSerializer(data=item, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    obj = s.save()

                    resposta['adicionados'].append(
                        OsHoraSerializer(obj, context={'banco': banco}).data
                    )

                # EDITAR
                for item in editar:
                    obrig = ['os_hora_item', 'os_hora_os', 'os_hora_empr', 'os_hora_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para edição faltando.")

                    try:
                        obj = OsHora.objects.using(banco).get(
                            os_hora_item=item['os_hora_item'],
                            os_hora_os=item['os_hora_os'],
                            os_hora_empr=item['os_hora_empr'],
                            os_hora_fili=item['os_hora_fili']
                        )
                    except OsHora.DoesNotExist:
                        continue

                    s = OsHoraSerializer(obj, data=item, partial=True, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    s.save()
                    resposta['editados'].append(s.data)

                # REMOVER
                for item in remover:
                    obrig = ['os_hora_item', 'os_hora_os', 'os_hora_empr', 'os_hora_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para remover faltando.")

                    OsHora.objects.using(banco).filter(
                        os_hora_item=item['os_hora_item'],
                        os_hora_os=item['os_hora_os'],
                        os_hora_empr=item['os_hora_empr'],
                        os_hora_fili=item['os_hora_fili']
                    ).delete()

                    resposta['removidos'].append(item['os_hora_item'])

            return tratar_sucesso(resposta)

        except Exception as e:
            return tratar_erro(e)



class MegaProdutosView(ModuloRequeridoMixin, APIView):

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config('savexml960' or '839' or 'casaa')
        if not banco:
            return tratar_erro(ErroDominio("Banco não encontrado.", codigo="banco_nao_encontrado"))

        try:
            empresa_id = request.headers.get('X-Empresa') or request.query_params.get('empr') or request.query_params.get('prod_empr') or 1
            filial_id = request.headers.get('X-Filial') or request.query_params.get('fili') or 1

            saldo_subquery = Subquery(
                SaldoProduto.objects.using(banco).filter(
                    produto_codigo=OuterRef('pk'),
                    empresa=empresa_id,
                    filial=filial_id
                ).values('saldo_estoque')[:1],
                output_field=DecimalField()
            )

            preco_vista_subquery = Subquery(
                Tabelaprecos.objects.using(banco).filter(
                    tabe_prod=OuterRef('prod_codi'),
                    tabe_empr=OuterRef('prod_empr')
                ).exclude(
                    tabe_entr__year__lt=1900
                ).exclude(
                    tabe_entr__year__gt=2100
                ).values('tabe_avis')[:1],
                output_field=DecimalField()
            )

            qs = Produtos.objects.using(banco).annotate(
                saldo_estoque=Coalesce(saldo_subquery, V(0), output_field=DecimalField()),
                prod_preco_vista=Coalesce(preco_vista_subquery, V(0), output_field=DecimalField()),
            )

            if empresa_id:
                qs = qs.filter(prod_empr=empresa_id)

            limit = int(request.query_params.get('limit') or 500)
            qs = qs.order_by('prod_empr', 'prod_codi')[:limit]

            data = [
                {
                    'prod_codi': p.prod_codi,
                    'prod_empr': p.prod_empr,
                    'prod_nome': p.prod_nome,
                    'preco_vista': float(getattr(p, 'prod_preco_vista', 0) or 0),
                    'saldo': float(getattr(p, 'saldo_estoque', 0) or 0),
                    'marca_nome': None,
                    'imagem_base64': None,
                }
                for p in qs
            ]

            return tratar_sucesso(data)
        except Exception as e:
            return tratar_erro(e)


class MegaEntidadesApiView(ModuloRequeridoMixin, APIView):


    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config('savexml960' or 'savexml839')
        if not banco:
            return tratar_erro(ErroDominio("Banco não encontrado.", codigo="banco_nao_encontrado"))

        try:
            empresa_id = request.headers.get('X-Empresa') or request.query_params.get('enti_empr')
            qs = Entidades.objects.using(banco).all()
            if empresa_id:
                qs = qs.filter(enti_empr=int(empresa_id))

            limit = int(request.query_params.get('limit') or 500)
            qs = qs.order_by('enti_empr', 'enti_nome')[:limit]

            data = [
                {
                    'enti_clie': e.enti_clie,
                    'enti_empr': e.enti_empr,
                    'enti_nome': e.enti_nome,
                    'enti_tipo_enti': e.enti_tipo_enti,
                    'enti_cpf': getattr(e, 'enti_cpf', None),
                    'enti_cnpj': getattr(e, 'enti_cnpj', None),
                    'enti_cida': getattr(e, 'enti_cida', None),
                }
                for e in qs
            ]

            return tratar_sucesso(data)
        except Exception as e:
            return tratar_erro(e)
