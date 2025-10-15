# mixins/vendedor_mixin.py
import logging

from Entidades.models import Entidades
from Licencas.models import Liberar
from core.utils import get_licenca_db_config

logger = logging.getLogger(__name__)

class VendedorEntidadeMixin:
    """
    Mixin reutilizável para identificar o vendedor vinculado ao usuário autenticado.
    Pode ser usado em qualquer ViewSet que precise filtrar dados por vendedor.
    """

    def get_entidade_vendedor(self, user=None, banco=None):
        """
        Retorna a entidade correspondente ao vendedor do usuário logado,
        ou None se o usuário não for associado a nenhum vendedor.
        """
        try:
            user = user or self.request.user
            banco = banco or get_licenca_db_config(self.request)
            empresa_id = self.request.headers.get("X-Empresa")

            liberar = Liberar.objects.using(banco).get(libe_usua=user.usua_codi)
            vendedor = Entidades.objects.using(banco).get(
                enti_clie=liberar.libe_codi_vend,
                enti_empr=empresa_id
            )

            logger.debug(f"✅ Vendedor identificado: {vendedor.enti_nome} (ID {vendedor.enti_clie})")
            return vendedor

        except (Liberar.DoesNotExist, Entidades.DoesNotExist):
            logger.warning(f"⚠️ Nenhuma entidade de vendedor encontrada para usuário {user.usua_codi}")
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
