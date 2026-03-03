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
            
        # Validação básica do formato: cliente_id_banco ou cliente_id_banco_usuario
        try:
            partes = session_id.split('_')
            
            # Tenta identificar o usuário logado (se houver)
            usuario_tipo = None
            if len(partes) >= 3 and partes[-1] in ['usuario1', 'usuario2']:
                usuario_tipo = partes[-1]
                cliente_id = int(partes[0])
                banco = '_'.join(partes[1:-1])
            else:
                # Formato antigo ou sem usuário específico
                cliente_id, banco = session_id.split('_', 1)
            
            request.cliente_id = int(cliente_id)
            request.banco = banco
            request.usuario_tipo = usuario_tipo
            
            # Carregar permissões da entidade
            from Entidades.models import Entidades
            try:
                # Usa filtro de empresa 1 para evitar duplicidade
                entidade = Entidades.objects.using(banco).filter(enti_clie=request.cliente_id, enti_empr=1).first()
                if not entidade:
                     # Fallback sem filtro de empresa
                     entidade = Entidades.objects.using(banco).filter(enti_clie=request.cliente_id).first()
                     
                if entidade:
                    if usuario_tipo == 'usuario1':
                        request.permissoes = {
                            'ver_preco': entidade.enti_mobi_prec,
                            'ver_foto': entidade.enti_mobi_foto
                        }
                    elif usuario_tipo == 'usuario2':
                        request.permissoes = {
                            'ver_preco': entidade.enti_usua_prec,
                            'ver_foto': entidade.enti_usua_foto
                        }
                    else:
                        # Fallback para comportamento antigo (AND) ou assumir usuario1?
                        # Melhor assumir usuario1 (mobi) como padrão se não identificado
                        request.permissoes = {
                            'ver_preco': entidade.enti_mobi_prec,
                            'ver_foto': entidade.enti_mobi_foto
                        }
                else:
                    request.permissoes = {'ver_preco': False, 'ver_foto': False}
            except Exception:
                request.permissoes = {'ver_preco': False, 'ver_foto': False}
                
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