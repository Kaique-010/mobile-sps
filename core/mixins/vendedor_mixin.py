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

    def _get_user_code(self, user=None):
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
        return user_code

    def _usuario_eh_perfil_vendedores(self, user=None, banco=None):
        """
        Valida se o usuário autenticado está no perfil 'vendedores'.
        Se perfilweb não estiver disponível/consistente, falha em modo permissivo.
        """
        try:
            banco = banco or get_licenca_db_config(self.request)
            user_code = self._get_user_code(user=user)
            if not user_code or not banco:
                return False

            from perfilweb.models import UsuarioPerfil
            return UsuarioPerfil.objects.using(banco).filter(
                perf_usua_id=user_code,
                perf_ativ=True,
                perf_perf__perf_ativ=True,
                perf_perf__perf_nome__iexact='vendedores',
            ).exists()
        except Exception as e:
            logger.warning(f"Falha ao validar perfil vendedores: {e}")
            return False

    def get_entidade_vendedor(self, user=None, banco=None):
        """
        Retorna a entidade do vendedor vinculada ao usuário atual.
        Fallbacks: request.user.usua_codi, sessão 'usua_codi'.
        """
        try:
            banco = banco or get_licenca_db_config(self.request)

            user_code = self._get_user_code(user=user)

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
        Se o usuário está no perfil 'vendedores', limita ao próprio vendedor.
        Se não estiver neste perfil, retorna queryset completo.
        """
        if not self._usuario_eh_perfil_vendedores():
            logger.debug("Usuário fora do perfil 'vendedores'. Nenhum filtro aplicado.")
            return queryset

        vendedor = self.get_entidade_vendedor()

        if vendedor:
            logger.debug(f"Filtrando queryset por vendedor {vendedor.enti_clie}")
            antes = queryset.count()
            queryset = queryset.filter(**{campo_vendedor: vendedor.enti_clie})
            depois = queryset.count()
            logger.debug(f"📊 Filtro aplicado: {antes} → {depois} registros")
        else:
            # Segurança: perfil vendedores sem entidade vinculada não enxerga dados de terceiros.
            logger.warning("Perfil vendedores sem entidade vinculada. Retornando queryset vazio.")
            queryset = queryset.none()

        return queryset

    def filter_por_nome_vendedor(self, queryset, campo_nome_vendedor):
        """
        Versão para datasets agregados (dashboards) com campo textual de vendedor.
        """
        if not self._usuario_eh_perfil_vendedores():
            return queryset

        vendedor = self.get_entidade_vendedor()
        if not vendedor:
            return queryset.none()

        nome_vendedor = (getattr(vendedor, 'enti_nome', '') or '').strip()
        if not nome_vendedor:
            return queryset.none()
        return queryset.filter(**{f"{campo_nome_vendedor}__iexact": nome_vendedor})
