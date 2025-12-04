# mixins/vendedor_mixin.py
import logging

from Entidades.models import Entidades
from Licencas.models import Liberar
from core.utils import get_licenca_db_config
from Licencas.models import Usuarios

logger = logging.getLogger(__name__)

class VendedorEntidadeMixin:
    """
    Mixin reutilizável para identificar o vendedor vinculado ao usuário autenticado.
    Pode ser usado em qualquer ViewSet que precise filtrar dados por vendedor.
    """

    def get_entidade_vendedor(self, user=None, banco=None):
        """
        Retorna a entidade do vendedor vinculada ao usuário atual.
        Fallbacks: request.user.usua_codi, sessão 'usua_codi'.
        """
        try:
            banco = banco or get_licenca_db_config(self.request)

            user_code = None
            if user is not None and hasattr(user, 'usua_codi'):
                user_code = getattr(user, 'usua_codi', None)
            elif getattr(self, 'request', None) is not None:
                req_user = getattr(self.request, 'user', None)
                if req_user is not None and hasattr(req_user, 'usua_codi'):
                    user_code = getattr(req_user, 'usua_codi', None)
                if not user_code:
                    try:
                        user_code = int(self.request.session.get('usua_codi'))
                    except Exception:
                        user_code = None

            if not user_code:
                logger.debug("Usuário não autenticado ou sem 'usua_codi'.")
                return None

            user = Usuarios.objects.using(banco).get(usua_codi=user_code)

            try:
                empresa_id = self.request.headers.get("X-Empresa") or self.request.session.get('empresa_id')
                liberar = Liberar.objects.using(banco).get(libe_usua=user.usua_codi)
                vendedor = Entidades.objects.using(banco).get(
                    enti_clie=liberar.libe_codi_vend,
                    enti_empr=int(empresa_id)
                )
                logger.debug(f"✅ Vendedor identificado: {vendedor.enti_nome} (ID {vendedor.enti_clie})")
                return vendedor
            except (Liberar.DoesNotExist, Entidades.DoesNotExist):
                logger.warning(f"⚠️ Nenhuma entidade de vendedor encontrada para usuário {user.usua_codi}")
                return None
        except Exception as e:
            logger.warning(f"Falha ao identificar vendedor: {e}")
            return None

    def filter_por_vendedor(self, queryset, campo_vendedor):
        """
        Filtra o queryset para retornar apenas registros associados ao vendedor do usuário logado.
        Se o usuário não for vendedor, retorna o queryset completo.
        """
        vendedor = self.get_entidade_vendedor()

        if vendedor:
            logger.debug(f"Filtrando queryset por vendedor {vendedor.enti_clie}")
            antes = queryset.count()
            queryset = queryset.filter(**{campo_vendedor: vendedor.enti_clie})
            depois = queryset.count()
            logger.debug(f"📊 Filtro aplicado: {antes} → {depois} registros")
        else:
            logger.debug("Usuário não é vendedor. Nenhum filtro aplicado.")

        return queryset
