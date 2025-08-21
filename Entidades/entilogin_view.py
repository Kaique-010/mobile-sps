
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework_simplejwt.tokens import RefreshToken
from Entidades.models import Entidades 
from django.db.models import Q
from core.registry import get_licenca_db_config, LICENCAS_MAP
from django.conf import settings
from django.db import connections
from decouple import config
import logging
from rest_framework.decorators import action
import jwt
from datetime import datetime, timedelta
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

class EntidadesLoginViewSet(viewsets.ViewSet):
    def create(self, request, slug=None):
        data = request.data
        documento = data.get('documento')  
        usuario = data.get('usuario')     
        senha = data.get('senha')        

        if not documento or not usuario or not senha:
            return Response({
                "erro": "Documento, usuário e senha são obrigatórios"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar em todas as licenças disponíveis
        for licenca in LICENCAS_MAP:
            try:
                banco_slug = licenca['slug']
                
                # Configurar banco se necessário
                if banco_slug not in settings.DATABASES:
                    self._configurar_banco(licenca)
                
                # Buscar entidade
                entidade = Entidades.objects.using(banco_slug).get(
                    Q(enti_cpf=documento) | Q(enti_cnpj=documento)
                )
                
                # Verificar credenciais
                if entidade.enti_mobi_usua == usuario and entidade.enti_mobi_senh == senha:
                    logger.info(f"[LOGIN SUCCESS] Cliente {entidade.enti_nome} - Banco: {banco_slug}")
                    
                    # Retorno simplificado - sem tokens
                    return Response({
                        'success': True,
                        'cliente_id': entidade.enti_clie,
                        'cliente_nome': entidade.enti_nome,
                        'documento': entidade.enti_cpf or entidade.enti_cnpj,
                        'banco': banco_slug,
                        'session_id': f"{entidade.enti_clie}_{banco_slug}"  # ID simples para sessão
                    })
                    
            except Entidades.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"[ERRO BANCO {banco_slug}] {str(e)}")
                continue
        
        logger.error(f"[LOGIN FAILED] Documento {documento} não encontrado")
        return Response({
            "erro": "Credenciais inválidas"
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    def _configurar_banco(self, licenca):
        """Configura banco dinamicamente"""
        prefixo = licenca["slug"].upper()
        try:
            db_user = config(f"{prefixo}_DB_USER")
            db_password = config(f"{prefixo}_DB_PASSWORD")
            
            settings.DATABASES[licenca["slug"]] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': licenca["db_name"],
                'USER': db_user,
                'PASSWORD': db_password,
                'HOST': licenca["db_host"],
                'PORT': licenca["db_port"],
                'OPTIONS': {
                    'options': '-c timezone=America/Araguaina'
                },
            }
            
            connections.ensure_defaults(licenca["slug"])
            
        except Exception as e:
            logger.error(f"[ERRO CONFIG BANCO] {licenca['slug']}: {str(e)}")
            raise





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
        "pedidovenda": "pedi_forn",  # Corrigido: era "pedidosvenda": "pedi_forn"
        "itenspedidosvenda": "iped_forn",
        "orcamentos": "pedi_forn",  # Corrigido: era "orcamentosvenda": "pedi_forn"
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
        "vfevv": "nota_clie",
    }

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


from Pedidos.models import PedidoVenda, PedidosGeral,Itenspedidovenda
from Orcamentos.models import Orcamentos,ItensOrcamento
from O_S.models import OrdemServicoGeral, Os
from OrdemdeServico.models import Ordemservico
from Pedidos.serializers import PedidoVendaSerializer, PedidosGeralSerializer,ItemPedidoVendaSerializer
from Orcamentos.serializers import OrcamentosSerializer,ItemOrcamentoSerializer
from O_S.serializers import OrdemServicoGeralSerializer, OsSerializer
from OrdemdeServico.serializers import OrdemServicoSerializer


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

class OsViewSet(BaseClienteViewSet):
    queryset = Os.objects.all()
    serializer_class = OsSerializer


class ClienteDashboardViewSet(viewsets.ViewSet):  # Mudar para ViewSet
    permission_classes = [IsCliente]
    
    def list(self, request):
        cliente_id = request.cliente_id
        banco = request.banco
        
        
        total_pedidos = PedidoVenda.objects.using(banco).filter(pedi_forn=cliente_id).count()
        total_orcamentos = Orcamentos.objects.using(banco).filter(pedi_forn=cliente_id).count()
        total_ordens_servico = Ordemservico.objects.using(banco).filter(orde_enti=cliente_id).count()
        total_os = Os.objects.using(banco).filter(os_clie=cliente_id).count()
        total_itens_pedidos = Itenspedidovenda.objects.using(banco).filter(iped_forn=cliente_id).count()
        total_itens_orcamentos = ItensOrcamento.objects.using(banco).filter(iped_forn=cliente_id).count()
        total_valor_pedidos = Itenspedidovenda.objects.using(banco).filter(iped_forn=cliente_id).aggregate(Sum('iped_valor'))['iped_valor__sum'] or 0
        total_valor_orcamentos = ItensOrcamento.objects.using(banco).filter(iped_forn=cliente_id).aggregate(Sum('iped_valor'))['iped_valor__sum'] or 0
        total_valor_ordens_servico = Ordemservico.objects.using(banco).filter(orde_enti=cliente_id).aggregate(Sum('orde_valor'))['orde_valor__sum'] or 0
        total_valor_os = Os.objects.using(banco).filter(os_clie=cliente_id).aggregate(Sum('os_valor'))['os_valor__sum'] or 0
        total_valor_total = total_valor_pedidos + total_valor_orcamentos + total_valor_ordens_servico + total_valor_os
        total_valor_total = round(total_valor_total, 2)

        dashboard_data = {
            'total_pedidos': 0,
            'total_orcamentos': 0, 
            'total_ordens_servico': 0,
            'valor_total': 0
        }
        
        return Response(dashboard_data)










