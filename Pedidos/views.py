from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound
from core.registry import get_licenca_db_config
from .models import Itenspedidovenda, PedidoVenda
from .serializers import PedidoVendaSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend



import logging
logger = logging.getLogger(__name__)


class PedidoVendaViewSet(ModuloRequeridoMixin,viewsets.ModelViewSet):
    modeulo_necessario = 'Pedidos'  
    permission_classes = [IsAuthenticated]
    serializer_class = PedidoVendaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    lookup_field = 'pedi_nume'
    search_fields = ['pedi_nume', 'pedi_forn']
    filterset_fields = ['pedi_empr', 'pedi_fili']
    
    def get_queryset(self):
       banco = get_licenca_db_config(self.request)
       if banco:
          return PedidoVenda.objects.using(banco).all().order_by('pedi_nume')
       else:
        logger.error("Banco de dados não encontrado.")
        raise NotFound("Banco de dados não encontrado.")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
    def create(self, request, *args, **kwargs):
        try:
            logger.info(f"[PedidoVendaViewSet.create] request.data: {request.data}")
        except Exception as e:
            logger.error(f"Erro ao acessar request.data: {e}")

        serializer = self.get_serializer(data=request.data, context=self.get_serializer_context())
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            logger.warning(f"[PedidoVendaViewSet.create] Erro de validação: {e.detail}")
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save()
        return Response(self.get_serializer(pedido).data, status=status.HTTP_200_OK)
    
    
    def destroy(self, request, *args, **kwargs):
        pedido = self.get_object()
        banco = get_licenca_db_config(self.request)
        
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

       
        if Itenspedidovenda.objects.using(banco).filter(
            iped_empr=pedido.pedi_empr,
            iped_fili=pedido.pedi_fili,
            iped_pedi=pedido.pedi_nume
        ).exists():
            return Response(
                {"detail": "Não é possível excluir a Pedidos , Há itens associados."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic(using=banco):
            pedido.delete()
            logger.info(f"🗑️ Exclusão Pedido de casamento ID {pedido.pedi_nume} concluída")

        return Response(status=status.HTTP_204_NO_CONTENT)