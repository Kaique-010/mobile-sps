

from re import T
from Pedidos.models import PedidoVenda, PedidosGeral,Itenspedidovenda
from Orcamentos.models import Orcamentos,ItensOrcamento
from O_S.models import  Os
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from OrdemdeServico.models import (
    Ordemservico,
    Ordemservicoimgantes,
    Ordemservicoimgdurante,
    Ordemservicoimgdepois
)
from Pedidos.rest.serializers import PedidoVendaSerializer, PedidosGeralSerializer, ItemPedidoVendaSerializer
from Orcamentos.rest.serializers import OrcamentosSerializer, ItemOrcamentoSerializer
from O_S.REST.serializers import OrdemServicoGeralSerializer, OsSerializer
from OrdemdeServico.serializers import (
    OrdemServicoSerializer,
    ImagemAntesSerializer,
    ImagemDuranteSerializer,
    ImagemDepoisSerializer
)
from .base_cliente import BaseClienteViewSet
from core.excecoes import ErroDominio
from core.dominio_handler import tratar_erro, tratar_sucesso


class PedidosViewSet(BaseClienteViewSet):
    queryset = PedidoVenda.objects.all()
    serializer_class = PedidoVendaSerializer

class PedidosGeralViewSet(BaseClienteViewSet):
    queryset = PedidosGeral.objects.all()
    serializer_class = PedidosGeralSerializer

class ItensPedidosVendaViewSet(BaseClienteViewSet):
    queryset = Itenspedidovenda.objects.all()
    serializer_class = ItemPedidoVendaSerializer

class ItensOrcamentoViewSet(BaseClienteViewSet):
    queryset = ItensOrcamento.objects.all()
    serializer_class = ItemOrcamentoSerializer


class OrcamentosViewSet(BaseClienteViewSet):
    queryset = Orcamentos.objects.all()
    serializer_class = OrcamentosSerializer

class OrdemServicoViewSet(BaseClienteViewSet):
    queryset = Ordemservico.objects.all()
    
    serializer_class = OrdemServicoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        status_param = self.request.query_params.get('status')
        data_inicial = self.request.query_params.get('data_inicial')
        data_final = self.request.query_params.get('data_final')

        if status_param:
            queryset = queryset.filter(orde_stat_orde=status_param)
        
        if data_inicial:
            queryset = queryset.filter(orde_data_aber__gte=data_inicial)
        
        if data_final:
            queryset = queryset.filter(orde_data_aber__lte=data_final)

        # BLINDAGEM CONTRA DATAS CORROMPIDAS (ex: ano -18)
        # Deferir campos de data que podem quebrar o driver psycopg2
        date_fields = [
            'orde_data_aber', 'orde_data_fech', 
            'orde_nf_data', 'orde_data_repr', 'orde_ulti_alte'
        ]
        queryset = queryset.defer(*date_fields)
        
        # Injetar campos seguros como texto
        select_dict = {}
        for field in date_fields:
            select_dict[f'safe_{field}'] = f"""
                CASE 
                    WHEN {field} IS NOT NULL 
                         AND EXTRACT(YEAR FROM {field}) BETWEEN 2020 AND 2100 
                    THEN {field}::text 
                    ELSE NULL 
                END
            """
        queryset = queryset.extra(select=select_dict)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='em-estoque')
    def listar_ordem_em_estoque(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset().filter(orde_stat_orde=22)
            print("ordens em estoque:", queryset)
            serializer = self.serializer_class(queryset, many=True)
            return tratar_sucesso(serializer.data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
    
    
    @action(detail=False, methods=['get'], url_path='imagensantes')
    def listar_imagens_antes(self, request, *args, **kwargs):
        try:
            orde_nume = request.query_params.get('orde_nume')
            if not orde_nume:
                raise ValueError("O parâmetro 'orde_nume' é obrigatório.")
            
            print(f"DEBUG: Buscando imagens ANTES para ordem {orde_nume} no banco {request.banco}")
            
            # Verificar se a ordem pertence ao cliente para obter empresa/filial corretas
            # E garantir segurança
            qs_ordem = Ordemservico.objects.using(request.banco).filter(
                orde_nume=orde_nume,
                orde_enti=request.cliente_id
            )
            
            if not qs_ordem.exists():
                print(f"DEBUG: Ordem {orde_nume} não encontrada para o cliente {request.cliente_id}")
                # Retorna vazio se não for do cliente
                return tratar_sucesso([])
                
            ordem = qs_ordem.first()
            print(f"DEBUG: Ordem encontrada. Empr: {ordem.orde_empr}, Fili: {ordem.orde_fili}")
                
            imagensAntes = Ordemservicoimgantes.objects.using(request.banco).filter(
                iman_orde=orde_nume,
                iman_empr=ordem.orde_empr,
                iman_fili=ordem.orde_fili
            )
            
            print(f"DEBUG: Encontrados {imagensAntes.count()} registros de imagens ANTES")
            
            for img in imagensAntes:
                tamanho = len(img.iman_imag) if img.iman_imag else 0
                print(f"DEBUG: Imagem ID {img.iman_id} tem tamanho {tamanho} bytes")

            context = self.get_serializer_context()
            serializer = ImagemAntesSerializer(imagensAntes, many=True, context=context)
            return tratar_sucesso(serializer.data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
        
        
    @action(detail=False, methods=['get'], url_path='imagensdepois')
    def listar_imagens_depois(self, request, *args, **kwargs):
        try:
            orde_nume = request.query_params.get('orde_nume')
            if not orde_nume:
                raise ValueError("O parâmetro 'orde_nume' é obrigatório.")

            print(f"DEBUG: Buscando imagens DEPOIS para ordem {orde_nume} no banco {request.banco}")
            
            qs_ordem = Ordemservico.objects.using(request.banco).filter(
                orde_nume=orde_nume,
                orde_enti=request.cliente_id
            )
            
            if not qs_ordem.exists():
                print(f"DEBUG: Ordem {orde_nume} não encontrada para o cliente {request.cliente_id}")
                return tratar_sucesso([])
                
            ordem = qs_ordem.first()

            imagensDepois = Ordemservicoimgdepois.objects.using(request.banco).filter(
                imde_orde=orde_nume,
                imde_empr=ordem.orde_empr,
                imde_fili=ordem.orde_fili
            )
            
            print(f"DEBUG: Encontrados {imagensDepois.count()} registros de imagens DEPOIS")

            for img in imagensDepois:
                tamanho = len(img.imde_imag) if img.imde_imag else 0
                print(f"DEBUG: Imagem ID {img.imde_id} tem tamanho {tamanho} bytes")

            context = self.get_serializer_context()
            serializer = ImagemDepoisSerializer(imagensDepois, many=True, context=context)
            return tratar_sucesso(serializer.data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
        
        
    @action(detail=False, methods=['get'], url_path='imagensdurante')
    def listar_imagens_durante(self, request, *args, **kwargs):
        try:
            orde_nume = request.query_params.get('orde_nume')
            if not orde_nume:
                raise ValueError("O parâmetro 'orde_nume' é obrigatório.")

            print(f"DEBUG: Buscando imagens DURANTE para ordem {orde_nume} no banco {request.banco}")
            
            qs_ordem = Ordemservico.objects.using(request.banco).filter(
                orde_nume=orde_nume,
                orde_enti=request.cliente_id
            )
            
            if not qs_ordem.exists():
                print(f"DEBUG: Ordem {orde_nume} não encontrada para o cliente {request.cliente_id}")
                return tratar_sucesso([])
                
            ordem = qs_ordem.first()

            imagensDurante = Ordemservicoimgdurante.objects.using(request.banco).filter(
                imdu_orde=orde_nume,
                imdu_empr=ordem.orde_empr,
                imdu_fili=ordem.orde_fili
            )
            
            print(f"DEBUG: Encontrados {imagensDurante.count()} registros de imagens DURANTE")

            for img in imagensDurante:
                tamanho = len(img.imdu_imag) if img.imdu_imag else 0
                print(f"DEBUG: Imagem ID {img.imdu_id} tem tamanho {tamanho} bytes")

            context = self.get_serializer_context()
            serializer = ImagemDuranteSerializer(imagensDurante, many=True, context=context)
            return tratar_sucesso(serializer.data)
        except (ErroDominio, ValueError) as e:
            return tratar_erro(e)
class OsViewSet(BaseClienteViewSet):
    queryset = Os.objects.all()
    serializer_class = OsSerializer