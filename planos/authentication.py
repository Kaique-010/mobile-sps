from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from licencas_web.models import LicencaWeb
import logging

logger = logging.getLogger(__name__)


class TrialAwareTokenObtainPairView(TokenObtainPairView):
    """
    Sobrescreve o endpoint de login JWT.
    Bloqueia com 403 se o plano trial do cliente estiver expirado ou inativo.
    """

    def post(self, request, *args, **kwargs):
        # Identifica o slug da licença (via header, query param ou body)
        slug = (
            request.headers.get('X-Licenca-Slug')
            or request.data.get('slug')
            or request.query_params.get('slug')
        )

        if slug:
            try:
                licenca = LicencaWeb.objects.select_related('plano').get(slug=slug)
                plano = licenca.plano

                if plano and plano.plan_trial:
                    # Verifica expiração no momento do login (defesa extra)
                    if not plano.plan_ativ:
                        return Response(
                            {
                                "detail": "Seu período de trial expirou. Entre em contato com o suporte.",
                                "code": "trial_expirado",
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )

                    # Segurança extra: plano ainda marcado ativo mas data já passou
                    if plano.plan_data_expi and timezone.now() > plano.plan_data_expi:
                        # Desativa na hora (garante consistência caso o Celery atrase)
                        plano.plan_ativ = False
                        plano.save(update_fields=['plan_ativ'])

                        logger.warning(
                            f"Trial expirado detectado no login — licença {slug}. "
                            f"Desativado on-the-fly."
                        )
                        return Response(
                            {
                                "detail": "Seu período de trial expirou. Entre em contato com o suporte.",
                                "code": "trial_expirado",
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )

            except LicencaWeb.DoesNotExist:
                logger.warning(f"Tentativa de login com slug inválido: {slug}")
                # Deixa o fluxo normal continuar (não vaza info de existência)

        return super().post(request, *args, **kwargs)