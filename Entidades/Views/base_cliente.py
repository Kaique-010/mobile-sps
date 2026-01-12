from rest_framework.permissions import BasePermission
from rest_framework import viewsets

class IsCliente(BasePermission):
    """Permissão simplificada para clientes"""
    
    def has_permission(self, request, view):
        # Verificar se tem session_id nos headers ou params
        session_id = (
            request.headers.get('X-Session-ID') or 
            request.GET.get('session_id') or
            request.data.get('session_id')
        )
        
        if not session_id:
            return False
            
        # Validação básica do formato: cliente_id_banco
        try:
            cliente_id, banco = session_id.split('_', 1)
            request.cliente_id = int(cliente_id)
            request.banco = banco
            return True
        except (ValueError, AttributeError):
            return False

class BaseClienteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCliente]
    
    cliente_field_map = {
        "pedidovenda": "pedi_forn",
        "itenspedidosvenda": "iped_forn",
        "orcamentos": "pedi_forn",
        "itensorcamentovenda": "iped_forn",
        "entidades": "enti_clie",
        "titulosreceber": "titu_clie",
        "titulospagar": "titu_forn",
        "baretitulos": "bare_clie",
        "bapatitulos": "bapa_forn",
        "contratosvendas": "cont_clie",
        "listacasamento": "list_noiv",
        "ordemservico": "orde_enti",
        "os": "os_clie",
        "ordemservico": "orde_enti",
        "vfevv": "nota_clie",
    }

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = self.request.banco
        return context

    def get_queryset(self):
        cliente_id = self.request.cliente_id
        banco = self.request.banco

        # pega o nome do modelo em minúsculo
        model_name = self.queryset.model.__name__.lower()

        # descobre o campo certo no mapa
        cliente_field = self.cliente_field_map.get(model_name)
        if not cliente_field:
            raise ValueError(f"Campo cliente não mapeado para o model {model_name}")

        filtro = {cliente_field: cliente_id}
        return self.queryset.using(banco).filter(**filtro)