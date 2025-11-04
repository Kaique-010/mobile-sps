from rest_framework.viewsets import ModelViewSet
from rest_framework import status, filters
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction, IntegrityError
from django.db.models import Max
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from .utils import get_next_item_number_sequence, get_next_service_id
from .models import Osflorestal, Osflorestalpecas, Osflorestalservicos
from .serializersOsFlorestal import (
    OsflorestalSerializer, OsflorestalpecasSerializer, OsflorestalservicosSerializer)
from django.db.models import Prefetch
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from datetime import datetime
import re

import logging
logger = logging.getLogger(__name__)


def sanitizar_data(data_str):
    """
    Sanitiza strings de data para formato YYYY-MM-DD
    Aceita formatos: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, ISO strings
    """
    if not data_str:
        return None
    
    # Se já é um objeto datetime, converte para string
    if isinstance(data_str, datetime):
        return data_str.strftime('%Y-%m-%d')
    
    # Remove espaços e caracteres especiais
    data_str = str(data_str).strip()
    
    # Se está vazio após limpeza
    if not data_str or data_str.lower() in ['null', 'none', '']:
        return None
    
    try:
        # Formato ISO (YYYY-MM-DD) ou datetime ISO
        if re.match(r'^\d{4}-\d{2}-\d{2}', data_str):
            # Extrai apenas a parte da data se for datetime completo
            data_parte = data_str.split('T')[0].split(' ')[0]
            datetime.strptime(data_parte, '%Y-%m-%d')
            return data_parte
        
        # Formato brasileiro DD/MM/YYYY
        elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', data_str):
            dt = datetime.strptime(data_str, '%d/%m/%Y')
            return dt.strftime('%Y-%m-%d')
        
        # Formato DD-MM-YYYY
        elif re.match(r'^\d{1,2}-\d{1,2}-\d{4}$', data_str):
            dt = datetime.strptime(data_str, '%d-%m-%Y')
            return dt.strftime('%Y-%m-%d')
        
        # Formato MM/DD/YYYY (americano)
        elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', data_str):
            # Tenta primeiro como DD/MM/YYYY, depois MM/DD/YYYY
            try:
                dt = datetime.strptime(data_str, '%d/%m/%Y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                dt = datetime.strptime(data_str, '%m/%d/%Y')
                return dt.strftime('%Y-%m-%d')
        
        else:
            logger.warning(f"Formato de data não reconhecido: {data_str}")
            return None
            
    except ValueError as e:
        logger.error(f"Erro ao converter data '{data_str}': {e}")
        return None


def sanitizar_dados_os(data):
    """
    Sanitiza os dados de uma ordem de serviço, focando nas datas
    """
    if not isinstance(data, dict):
        return data
    
    # Campos de data da OS principal
    campos_data_os = ['osfl_data_aber', 'osfl_data_entr', 'osfl_data_fech']
    
    for campo in campos_data_os:
        if campo in data:
            data[campo] = sanitizar_data(data[campo])
    
    # Sanitizar datas em peças (se existirem)
    if 'pecas' in data and isinstance(data['pecas'], list):
        for peca in data['pecas']:
            if isinstance(peca, dict):
                # Peças não têm campos de data específicos no modelo atual
                pass
    
    # Sanitizar datas em serviços (se existirem)
    if 'servicos' in data and isinstance(data['servicos'], list):
        for servico in data['servicos']:
            if isinstance(servico, dict) and 'serv_data' in servico:
                servico['serv_data'] = sanitizar_data(servico['serv_data'])
    
    return data


class BaseMultiDBModelViewSet(ModuloRequeridoMixin, ModelViewSet):
    permission_classes = [IsAuthenticated]

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
        
        # Sanitizar datas se for uma OS
        data = request.data
        if hasattr(instance, 'osfl_orde'):  # É uma OS
            data = sanitizar_dados_os(request.data.copy())
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            serializer.save()
        return Response(serializer.data)


class OsViewSet(BaseMultiDBModelViewSet):
    permission_classes = [IsAuthenticated]
    modulo_necessario = 'Florestal'
    serializer_class = OsflorestalSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['osfl_stat', 'osfl_forn']
    ordering_fields = ['osfl_data_aber', 'osfl_data_fech']
    search_fields = ['osfl_prob_rela', 'osfl_obse']
   
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def get_queryset(self):
        banco = self.get_banco()
        user_setor = getattr(self.request.user, 'setor', None)
        
        # Filtro base
        qs = Osflorestal.objects.using(banco).all()
        
        # Filtrar por setor do usuário se não for admin (setor 6)
        if user_setor and hasattr(user_setor, 'osfs_codi') and user_setor.osfs_codi != 6:
            qs = qs.filter(osfl_seto=user_setor.osfs_codi)
        
        # Aplicar filtros para datas válidas em todos os campos de data
        # Excluir registros com anos inválidos (< 1900 ou > 2100) ou NULL
        from django.db.models import Q
        
        # Filtro para osfl_data_aber: deve ser NULL ou ter ano válido
        qs = qs.filter(
            Q(osfl_data_aber__isnull=True) | 
            Q(osfl_data_aber__year__gte=1900, osfl_data_aber__year__lte=2100)
        )
        
        # Filtro para osfl_data_entr: deve ser NULL ou ter ano válido
        qs = qs.filter(
            Q(osfl_data_entr__isnull=True) | 
            Q(osfl_data_entr__year__gte=1900, osfl_data_entr__year__lte=2100)
        )
        
        # Filtro para osfl_data_fech: deve ser NULL ou ter ano válido
        qs = qs.filter(
            Q(osfl_data_fech__isnull=True) | 
            Q(osfl_data_fech__year__gte=1900, osfl_data_fech__year__lte=2100)
        )
        

        
        return qs.order_by('-osfl_data_aber')
        
    @action(detail=True, methods=['post'])
    def finalizar_os(self, request, pk=None):
        """Endpoint para finalizar uma OS com validações"""
        os_instance = self.get_object()
        
        # Validações de negócio
        if os_instance.osfl_stat == 2:
            return Response(
                {'error': 'OS já finalizada'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar se tem peças ou serviços
        banco = self.get_banco()
        tem_pecas = Osflorestalpecas.objects.using(banco).filter(
            peca_os=os_instance.osfl_os
        ).exists()
        tem_servicos = Osflorestalservicos.objects.using(banco).filter(
            serv_os=os_instance.osfl_os
        ).exists()
        
        if not tem_pecas and not tem_servicos:
            return Response(
                {'error': 'OS deve ter pelo menos uma peça ou serviço'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic(using=banco):
            os_instance.osfl_stat = 2
            os_instance.osfl_data_fech = timezone.now().date()  
            os_instance.save(using=banco)
        
        return Response({'message': 'OS finalizada com sucesso'})

    def get_next_ordem_numero(self, empre, fili):
        banco = self.get_banco()
        ultimo = Osflorestal.objects.using(banco).filter(osfl_empr=empre, osfl_fili=fili).aggregate(Max('osfl_orde'))['osfl_orde__max']
        return (ultimo or 0) + 1

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        data = request.data.copy()

        # Sanitizar datas antes do processamento
        data = sanitizar_dados_os(data)

        data['osfl_stat'] = 0
        if request.user and request.user.pk:
            data['osfl_usua_aber'] = request.user.pk

        # Se não há data de abertura, define como hoje
        if not data.get('osfl_data_aber'):
            data['osfl_data_aber'] = timezone.now().date().strftime('%Y-%m-%d')

        empre = data.get('osfl_empr') or data.get('empr')
        fili = data.get('osfl_fili') or data.get('fili')
        if not empre or not fili:
            return Response({"detail": "Empresa e Filial são obrigatórios."}, status=400)

        data['osfl_orde'] = self.get_next_ordem_numero(empre, fili)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic(using=banco):
            instance = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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


class PecasOsViewSet(BaseMultiDBModelViewSet,ModelViewSet):
    serializer_class = OsflorestalpecasSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
 
   
    def atualizar_total_ordem(self, peca_empr, peca_fili, peca_orde):
        banco = self.get_banco()
        try:
            ordem = Osflorestal.objects.using(banco).get(
                osfl_empr=peca_empr,
                osfl_fili=peca_fili,
                osfl_orde=peca_orde
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Osflorestal.DoesNotExist:
            logger.error(f"Ordem de serviço não encontrada: {peca_orde}")

    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_empr = self.request.query_params.get('peca_empr')
        peca_fili = self.request.query_params.get('peca_fili')
        peca_orde = self.request.query_params.get('peca_orde')

        if not all([peca_empr, peca_fili, peca_orde]):
            logger.warning("Parâmetros obrigatórios não fornecidos (peca_empr, peca_fili, peca_orde)")
            return Osflorestalpecas.objects.none()

        queryset = Osflorestalpecas.objects.using(banco).filter(
            peca_empr=peca_empr,
            peca_fili=peca_fili,
            peca_orde=peca_orde
        )

       

        logger.info(f"Parâmetros recebidos: peca_empr={peca_empr}, peca_fili={peca_fili}, peca_orde={peca_orde}")
        logger.info(f"Queryset filtrado: {queryset.query}")
        return queryset.order_by('peca_item')

    def get_object(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        peca_item = self.kwargs.get('pk')
        peca_orde = self.request.query_params.get("peca_orde")
        peca_empr = self.request.query_params.get("peca_empr")
        peca_fili = self.request.query_params.get("peca_fili")

        if not all([peca_orde, peca_empr, peca_fili, peca_item]):
            raise ValidationError("Parâmetros peca_orde, peca_empr, peca_fili e pk (peca_item) são obrigatórios.")

        try:
            return self.get_queryset().get(
                peca_item=peca_item,
                peca_orde=peca_orde,
                peca_empr=peca_empr,
                peca_fili=peca_fili
            )
        except Osflorestalpecas.DoesNotExist:
            raise NotFound("peca não encontrado na lista especificada.")
        except Osflorestalpecas.MultipleObjectsReturned:
            raise ValidationError("Mais de um peca encontrado com essa chave composta.")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def destroy(self, request, *args, **kwargs):
        peca = self.get_object()
       
        return super().destroy(request, *args, **kwargs)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        banco = get_licenca_db_config(self.request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        try:
            logger.info(f"Criação de peca(s) por {request.user.pk if request.user else 'None'}")

            if isinstance(request.data, list):
                serializer = self.get_serializer(data=request.data, many=True)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return super().create(request, *args, **kwargs)

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response({'detail': 'Erro de integridade.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
  
  
  
    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=404)

        data = request.data
        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):
                # Validar e adicionar novos itens
                for item in adicionar:
                    # Validar campos obrigatórios
                    campos_obrigatorios = ['peca_orde', 'peca_empr', 'peca_fili', 'peca_prod']  
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

                    # Converter campos numéricos
                    try:
                        item['peca_orde'] = int(item['peca_orde'])
                        item['peca_empr'] = int(item['peca_empr'])
                        item['peca_fili'] = int(item['peca_fili'])
                        item['peca_quan'] = float(item.get('peca_quan', 0))
                        item['peca_unit'] = float(item.get('peca_unit', 0))
                        item['peca_tota'] = float(item.get('peca_tota', 0))
                    except (ValueError, TypeError) as e:
                        raise ValidationError({
                            'error': f"Erro ao converter valores numéricos: {str(e)}",
                            'item': item
                        })

                    item['peca_item'] = get_next_item_number_sequence(
                        banco, item['peca_orde'], item['peca_empr'], item['peca_fili']
                    )
                    serializer = OsflorestalpecasSerializer(data=item, context={'banco': banco})
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()

                    obj_refetch = Osflorestalpecas.objects.using(banco).get(
                        peca_empr=obj.peca_empr,
                        peca_fili=obj.peca_fili,
                        peca_orde=obj.peca_orde,
                        peca_item=obj.peca_item,
                    )
                    resposta['adicionados'].append(
                        OsflorestalpecasSerializer(obj_refetch, context={'banco': banco}).data
                    )

                # Validar e editar itens existentes
                for item in editar:
                    if not all(k in item for k in ['peca_item', 'peca_orde', 'peca_empr', 'peca_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para edição",
                            'item': item
                        })

                    try:
                        obj = Osflorestalpecas.objects.using(banco).get(
                            peca_item=item['peca_item'],
                            peca_orde=item['peca_orde'],
                            peca_empr=item['peca_empr'],
                            peca_fili=item['peca_fili']
                        )
                    except Osflorestalpecas.DoesNotExist:
                        logger.warning(f"Peça não encontrada para edição: {item}")
                        continue

                    serializer = OsflorestalpecasSerializer(obj, data=item, context={'banco': banco}, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    resposta['editados'].append(serializer.data)

                # Validar e remover itens
                for item in remover:
                    if not all(k in item for k in ['peca_item', 'peca_orde', 'peca_empr', 'peca_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para remoção",
                            'item': item
                        })

                    Osflorestalpecas.objects.using(banco).filter(
                        peca_item=item['peca_item'],
                        peca_orde=item['peca_orde'],
                        peca_empr=item['peca_empr'],
                        peca_fili=item['peca_fili']
                    ).delete()
                    resposta['removidos'].append(item['peca_item'])

            return Response(resposta)
        

        except ValidationError as e:
            logger.error(f"Erro de validação ao processar update_lista: {str(e)}")
            return Response(e.detail, status=400)
        except Exception as e:
            logger.error(f"Erro ao processar update_lista: {str(e)}")
            return Response({"error": str(e)}, status=400)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:  # Se criou com sucesso
            data = request.data
            self.atualizar_total_ordem(
                data.get('peca_empr'),
                data.get('peca_fili'),
                data.get('peca_orde')
            )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:  # Se atualizou com sucesso
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.peca_empr,
                instance.peca_fili,
                instance.peca_os
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.peca_empr, instance.peca_fili, instance.peca_os
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:  # Se deletou com sucesso
            self.atualizar_total_ordem(empr, fili, orde)
        return response

class ServicosOsViewSet(BaseMultiDBModelViewSet):
    modulo_necessario = 'O_S'
    serializer_class = OsflorestalservicosSerializer    
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def atualizar_total_ordem(self, serv_empr, serv_fili, serv_orde):
        banco = self.get_banco()
        try:
            ordem = Osflorestal.objects.using(banco).get(
                osfl_empr=serv_empr,
                osfl_fili=serv_fili,
                osfl_orde=serv_orde
            )
            ordem.calcular_total()
            ordem.save(using=banco)
        except Osflorestal.DoesNotExist:
            logger.error(f"Ordem de serviço não encontrada: {serv_orde}")

    def get_queryset(self):
        banco = self.get_banco()
        serv_empr = self.request.query_params.get('serv_empr') or self.request.query_params.get('empr')
        serv_fili = self.request.query_params.get('serv_fili') or self.request.query_params.get('fili')
        serv_orde = self.request.query_params.get('serv_orde') or self.request.query_params.get('ordem')

        if not all([serv_empr, serv_fili, serv_orde]):
            logger.warning("Parâmetros obrigatórios não fornecidos (serv_empr/empr, serv_fili/fili, serv_orde/ordem)")
            return Osflorestalservicos.objects.using(banco).none()

        qs = Osflorestalservicos.objects.using(banco).filter(
            serv_empr=serv_empr,
            serv_fili=serv_fili,
            serv_orde=serv_orde
        )
        
        logger.info(f"Filtrando serviços com: ordem={serv_orde}, empresa={serv_empr}, filial={serv_fili}")
        return qs.order_by('serv_item')

    @action(detail=False, methods=['post'], url_path='update-lista')
    def update_lista(self, request, slug=None):
        banco = self.get_banco()
        if not banco:
            return Response({"error": "Banco de dados não encontrado."}, status=404)

        data = request.data
        adicionar = data.get('adicionar', [])
        editar = data.get('editar', [])
        remover = data.get('remover', [])

        resposta = {'adicionados': [], 'editados': [], 'removidos': []}

        try:
            with transaction.atomic(using=banco):
                # ADICIONAR
                for item in adicionar:
                    # Verifica campos obrigatórios
                    campos_obrigatorios = ['serv_orde', 'serv_empr', 'serv_fili', 'serv_prod']
                    campos_faltantes = [campo for campo in campos_obrigatorios if not item.get(campo)]
                    if campos_faltantes:
                        raise ValidationError({
                            'error': f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}",
                            'item': item
                        })

                    # Converte campos numéricos
                    try:
                        item['serv_orde'] = int(item['serv_orde'])
                        item['serv_empr'] = int(item['serv_empr'])
                        item['serv_fili'] = int(item['serv_fili'])
                        item['serv_quan'] = float(item.get('serv_quan') or 0)
                        item['serv_unit'] = float(item.get('serv_unit') or 0)
                        item['serv_tota'] = float(item.get('serv_tota') or (item['serv_quan'] * item['serv_unit']))
                    except (ValueError, TypeError) as e:
                        raise ValidationError({
                            'error': f"Erro ao converter valores numéricos: {str(e)}",
                            'item': item
                        })

                    # Gera novo ID sequencial (recebe tupla)
                    novo_id, _ = get_next_service_id(
                        banco,
                        item['serv_orde'],
                        item['serv_empr'],
                        item['serv_fili']
                    )
                    item['serv_item'] = novo_id

                    # Cria via serializer
                    serializer = self.get_serializer(data=item, context={'banco': banco})
                    serializer.is_valid(raise_exception=True)
                    obj = serializer.save()
                    resposta['adicionados'].append(serializer.data)

                # EDITAR
                for item in editar:
                    if not all(k in item for k in ['serv_item', 'serv_orde', 'serv_empr', 'serv_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para edição",
                            'item': item
                        })

                    try:
                        obj = Osflorestalservicos.objects.using(banco).get(
                            serv_item=item['serv_item'],
                            serv_orde=item['serv_orde'],
                            serv_empr=item['serv_empr'],
                            serv_fili=item['serv_fili']
                        )
                        serializer = self.get_serializer(obj, data=item, partial=True, context={'banco': banco})
                        serializer.is_valid(raise_exception=True)
                        serializer.save()
                        resposta['editados'].append(serializer.data)
                    except Osflorestalservicos.DoesNotExist:
                        logger.warning(f"Serviço não encontrado para edição: {item}")
                        continue

                # REMOVER
                for item in remover:
                    if not all(k in item for k in ['serv_item', 'serv_orde', 'serv_empr', 'serv_fili']):
                        raise ValidationError({
                            'error': "Campos obrigatórios faltando para remoção",
                            'item': item
                        })

                    deleted, _ = Osflorestalservicos.objects.using(banco).filter(
                        serv_item=item['serv_item'],
                        serv_orde=item['serv_orde'],
                        serv_empr=item['serv_empr'],
                        serv_fili=item['serv_fili']
                    ).delete()

                    if deleted:
                        resposta['removidos'].append(item['serv_item'])

            return Response(resposta)

        except ValidationError as e:
            logger.error(f"Erro de validação ao processar update_lista: {str(e)}")
            return Response(e.detail, status=400)

        except Exception as e:
            logger.exception("Erro inesperado ao processar update_lista")
            return Response({"error": str(e)}, status=400)


    def create(self, request, *args, **kwargs):
        # Sanitizar data do serviço
        data = request.data.copy()
        if 'serv_data' in data:
            data['serv_data'] = sanitizar_data(data['serv_data'])
        
        # Atualizar request.data com dados sanitizados
        request._full_data = data
        
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:  # Se criou com sucesso
            self.atualizar_total_ordem(
                data.get('serv_empr'),
                data.get('serv_fili'),
                data.get('serv_orde')
            )
        return response

    def update(self, request, *args, **kwargs):
        # Sanitizar data do serviço
        data = request.data.copy()
        if 'serv_data' in data:
            data['serv_data'] = sanitizar_data(data['serv_data'])
        
        # Atualizar request.data com dados sanitizados
        request._full_data = data
        
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:  # Se atualizou com sucesso
            instance = self.get_object()
            self.atualizar_total_ordem(
                instance.serv_empr,
                instance.serv_fili,
                instance.serv_orde
            )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        empr, fili, orde = instance.serv_empr, instance.serv_fili, instance.serv_orde
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:  # Se deletou com sucesso
            self.atualizar_total_ordem(empr, fili, orde)
        return response

