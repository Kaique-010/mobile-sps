from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework import status, filters
from rest_framework.response import Response
from django.http import HttpResponse
from core.impressoes.documentos.os import OrdemServicoPrinter
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction, IntegrityError
from django.db.models import Max
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

import logging
logger = logging.getLogger(__name__)
import base64


class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):

    def get_banco(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error(f"Banco de dados não encontrado para {self.__class__.__name__}")
            raise NotFound("Banco de dados não encontrado.")
        return banco

    def get_queryset(self):
        return super().get_queryset().using(self.get_banco())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    @transaction.atomic(using='default')
    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data
        is_many = isinstance(data, list)
        serializer = self.get_serializer(data=data, many=is_many)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        banco = self.get_banco()
        partial = kwargs.pop('partial', False)
        instance = self.get_object()        
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data)


class OsViewSet(BaseMultiDBModelViewSet):
    permission_classes = [PodeVerOrdemDoSetor]
    serializer_class = OsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['os_stat_os', 'os_clie', 'os_empr', 'os_fili']
    ordering_fields = ['os_os']
    search_fields = ['os_prob_rela', 'os_obse']
   
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.get_banco()
        return context

    def get_queryset(self):
        banco = self.get_banco()
        empresa = self.request.query_params.get('os_empr') or self.request.query_params.get('empresa_id') 
        filial = self.request.query_params.get('os_fili') or self.request.query_params.get('filial_id')
        qs = Os.objects.using(banco).filter(os_empr=empresa, os_fili=filial)

        return qs.order_by('-os_os')
    
    def get_object(self):
        banco = self.get_banco()
        try:
            logger.info(f"Buscando OS com pk={self.kwargs['pk']} no banco {banco}")
            return Os.objects.using(banco).get(pk=self.kwargs['pk'])
        except Os.DoesNotExist:
            raise NotFound("Ordem de Serviço não encontrada.")
        
    @action(detail=True, methods=['post'])
    def finalizar_os(self, request, pk=None):
        """Endpoint para finalizar uma OS com validações"""
        os_instance = self.get_object()
        
        # Validações de negócio
        if os_instance.os_stat_os == 2:
            return Response(
                {'error': 'OS já finalizada'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar se tem peças ou serviços
        banco = self.get_banco()
        tem_pecas = PecasOs.objects.using(banco).filter(
            peca_os=os_instance.os_os
        ).exists()
        tem_servicos = ServicosOs.objects.using(banco).filter(
            serv_os=os_instance.os_os
        ).exists()
        
        if not tem_pecas and not tem_servicos:
            return Response(
                {'error': 'OS deve ter pelo menos uma peça ou serviço'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic(using=banco):
            os_instance.os_stat_os = 2
            os_instance.os_data_fech = timezone.now().date()
            os_instance.save(using=banco)
        
        return Response({'message': 'OS finalizada com sucesso'})

    def get_next_ordem_numero(self, empre, fili):
        banco = self.get_banco()
        ultimo = Os.objects.using(banco).filter(os_empr=empre, os_fili=fili).aggregate(Max('os_os'))['os_os__max']
        return (ultimo or 0) + 1
    
    

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        base_data = request.data.copy()

        base_data['os_stat_os'] = 0
        if request.user and request.user.pk:
            base_data['os_usua_aber'] = request.user.pk

        empre = base_data.get('os_empr') or base_data.get('empr')
        fili = base_data.get('os_fili') or base_data.get('fili')
        if not empre or not fili:
            return Response({"detail": "Empresa e Filial são obrigatórios."}, status=400)

        base_data['os_prof_aber'] = request.user.pk if request.user else None

        # Tentativas para lidar com concorrência e colisões de número
        max_tentativas = 5
        for tentativa in range(max_tentativas):
            data = base_data.copy()
            data['os_os'] = self.get_next_ordem_numero(empre, fili)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            try:
                with transaction.atomic(using=banco):
                    instance = serializer.save()
                logger.info(
                    f"O.S. {instance.os_os} aberta por user {request.user.pk if request.user else 'anon'}"
                )
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED,
                    headers=headers,
                )
            except IntegrityError:
                logger.warning(
                    f"Colisão de número de OS detectada (tentativa {tentativa+1}/{max_tentativas}). Recalculando..."
                )
                continue

        return Response(
            {"detail": "Falha ao gerar número da O.S. Tente novamente."},
            status=status.HTTP_409_CONFLICT,
        )

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
                ordem.calcular_total()
                ordem.save(using=banco)
            
            serializer = self.get_serializer(ordem)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Erro ao atualizar total da ordem {pk}: {str(e)}")
            return Response(
                {"error": "Erro ao atualizar total da ordem de serviço"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['patch'], url_path='patch')
    def patch_ordem(self, request, slug=None):
        banco = self.get_banco()
        os_pk = request.data.get('os_os') or request.data.get('pk')
        if not os_pk:
            return Response({'detail': 'os_os obrigatório'}, status=400)
        try:
            instance = Os.objects.using(banco).get(pk=os_pk)
        except Os.DoesNotExist:
            raise NotFound('Ordem de Serviço não encontrada.')
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data)
    
    
    @action(detail=True, methods=['get'])
    def imprimir(self, request, pk=None, slug=None):
        """
        Endpoint para imprimir uma Ordem de Serviço em PDF.
        
        URL: /api/ordem-servico/{id}/imprimir/
        Método: GET
        
        Returns:
            HttpResponse com PDF inline (visualização no navegador)
        """
        # ===============================================================
        # 1. BUSCA DADOS DO BANCO
        # ===============================================================
        
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
            
            Banco de dados pode retornar:
            - memoryview (PostgreSQL bytea)
            - bytes (SQLite blob)
            - None (sem assinatura)
            
            Returns:
                String base64 ou None
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
            raise ValidationError("Faltam parâmetros: peca_item, peca_os, peca_empr, peca_fili.")

        try:
            return PecasOs.objects.using(banco).get(
                peca_item=peca_item,
                peca_os=peca_os,
                peca_empr=peca_empr,
                peca_fili=peca_fili
            )
        except PecasOs.DoesNotExist:
            raise NotFound("Peça não encontrada.")
        except PecasOs.MultipleObjectsReturned:
            raise ValidationError("Chave composta retornou múltiplos registros.")

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

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except IntegrityError:
            return Response({'detail': 'Erro de integridade.'}, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({'detail': str(e)}, status=500)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.peca_empr, instance.peca_fili, instance.peca_os
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.peca_empr, instance.peca_fili, instance.peca_os
        response = super().destroy(request, *args, **kwargs)

        if response.status_code == 204:
            self.atualizar_total_ordem(empr, fili, orde)

        return response

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

            return Response(resposta)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({"error": str(e)}, status=400)



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
            raise ValidationError("Campos serv_os, serv_empr, serv_fili e pk (serv_item) são obrigatórios.")

        try:
            return self.get_queryset().get(
                serv_item=serv_item,
                serv_os=serv_os,
                serv_empr=serv_empr,
                serv_fili=serv_fili
            )
        except ServicosOs.DoesNotExist:
            raise NotFound("Serviço não encontrado na lista especificada.")
        except ServicosOs.MultipleObjectsReturned:
            raise ValidationError("Mais de um serviço encontrado com essa chave composta.")

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

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except IntegrityError:
            return Response({'detail': 'Erro de integridade.'}, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({'detail': str(e)}, status=500)

    # ---- UPDATE ----
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.serv_empr,
                instance.serv_fili,
                instance.serv_os
            )
        return response

    # ---- DELETE ----
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.serv_empr, instance.serv_fili, instance.serv_os
        response = super().destroy(request, *args, **kwargs)

        if response.status_code == 204:
            self.atualizar_total_ordem(empr, fili, orde)

        return response

    # ---- UPDATE LISTA (LOTE) ----
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
                    obrig = ['serv_os', 'serv_empr', 'serv_fili', 'serv_prod']
                    faltando = [c for c in obrig if not item.get(c)]
                    if faltando:
                        raise ValidationError(f"Faltam campos: {', '.join(faltando)}")

                    item['serv_item'] = get_next_global_serv_item_id(banco)

                    s = ServicosOsSerializer(data=item, context={'banco': banco})
                    s.is_valid(raise_exception=True)
                    obj = s.save()

                    resposta['adicionados'].append(
                        ServicosOsSerializer(obj, context={'banco': banco}).data
                    )

                # EDITAR
                for item in editar:
                    obrig = ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para edição faltando.")

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
                    obrig = ['serv_item', 'serv_os', 'serv_empr', 'serv_fili']
                    if not all(k in item for k in obrig):
                        raise ValidationError("Campos obrigatórios para remover faltando.")

                    ServicosOs.objects.using(banco).filter(
                        serv_item=item['serv_item'],
                        serv_os=item['serv_os'],
                        serv_empr=item['serv_empr'],
                        serv_fili=item['serv_fili']
                    ).delete()

                    resposta['removidos'].append(item['serv_item'])

            return Response(resposta)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({"error": str(e)}, status=400)



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
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
    
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
                raise NotFound("Registro de horas não encontrado")
            except OsHora.MultipleObjectsReturned:
                raise ValidationError("Múltiplos registros encontrados. Forneça os_hora_os, os_hora_empr e os_hora_fili para identificar unicamente.")

        if not all([os_hora_item, os_hora_os, os_hora_empr, os_hora_fili]):
            logger.error(f"Parâmetros faltando OsHoraViewSet.get_object: kwargs={self.kwargs}, query={self.request.query_params}")
            raise ValidationError("Parâmetros obrigatórios faltando")
        
        try:
            return OsHora.objects.using(banco).get(
                os_hora_item=os_hora_item,
                os_hora_os=os_hora_os,
                os_hora_empr=os_hora_empr,
                os_hora_fili=os_hora_fili
            )
        except OsHora.DoesNotExist:
            raise NotFound("Registro de horas não encontrado")
    
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
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(f"Erro ao criar registro de horas: {str(e)}")
            return Response({'detail': str(e)}, status=500)
    
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
        banco = self.get_banco()
        
        os_hora_os = request.query_params.get('os_hora_os')
        os_hora_empr = request.query_params.get('os_hora_empr')
        os_hora_fili = request.query_params.get('os_hora_fili')
        
        if not all([os_hora_os, os_hora_empr, os_hora_fili]):
            return Response(
                {'error': 'Parâmetros obrigatórios faltando'},
                status=400
            )
        
        registros = OsHora.objects.using(banco).filter(
            os_hora_os=os_hora_os,
            os_hora_empr=os_hora_empr,
            os_hora_fili=os_hora_fili
        )
        
        total = 0.0
        for registro in registros:
            serializer = OsHoraSerializer(registro, context={'banco': banco})
            total += serializer.data.get('total_horas', 0)
        
        return Response({
            'total_horas': round(total, 2),
            'total_registros': registros.count()
        })
    
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

            return Response(resposta)

        except ValidationError as e:
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(str(e))
            return Response({"error": str(e)}, status=400)



class MegaProdutosView(ModuloRequeridoMixin, APIView):

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config('savexml960')
        if not banco:
            return Response({"detail": "Banco não encontrado."}, status=400)

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

            return Response(data)
        except Exception as e:
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)


class MegaEntidadesApiView(ModuloRequeridoMixin, APIView):


    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config('savexml960')
        if not banco:
            return Response({"detail": "Banco não encontrado."}, status=400)

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

            return Response(data)
        except Exception as e:
            return Response({'detail': f'Erro interno: {str(e)}'}, status=500)
