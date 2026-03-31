from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def verificar_trials_expirados(self):
    """
    Roda diariamente via Celery Beat.
    Desativa planos trial expirados e envia e-mail ao cliente.
    """
    from .models import Plano
    from licencas_web.models import LicencaWeb

    agora = timezone.now()
    
    planos_expirados = Plano.objects.filter(
        plan_ativ=True,
        plan_trial=True,
        plan_data_expi__lt=agora
    )

    total = planos_expirados.count()
    logger.info(f"[Trial Check] {total} plano(s) expirado(s) encontrado(s).")

    for plano in planos_expirados:
        try:
            plano.plan_ativ = False
            plano.save(update_fields=['plan_ativ'])

            # Busca e-mail via LicencaWeb → Empresa
            licenca = LicencaWeb.objects.filter(plano=plano).first()
            if licenca:
                _enviar_email_expiracao(plano, licenca)

        except Exception as exc:
            logger.error(f"Erro ao expirar plano {plano.id}: {exc}")
            raise self.retry(exc=exc, countdown=60 * 10)

    return f"{total} plano(s) expirado(s) com sucesso."


def _enviar_email_expiracao(plano, licenca):
    """Envia e-mail informando que o trial expirou."""
    from Licencas.models import Empresas
    from core.utils import get_db_from_slug

    email_destino = None
    nome_empresa = plano.plan_nome

    try:
        db_alias = get_db_from_slug(licenca.slug)
        empresa = Empresas.objects.using(db_alias).filter(empr_codi=1).first()
        if empresa:
            email_destino = empresa.empr_emai
            nome_empresa = empresa.empr_nome
    except Exception as e:
        logger.warning(f"Não foi possível buscar empresa para e-mail: {e}")
        email_destino = licenca.cnpj  # fallback — adapte conforme seu model

    if not email_destino:
        logger.warning(f"Nenhum e-mail encontrado para licença {licenca.slug}. Pulando envio.")
        return

    try:
        send_mail(
            subject="Seu período de teste expirou",
            message=(
                f"Olá, {nome_empresa}!\n\n"
                f"Seu trial de 15 dias encerrou em {licenca.plano.plan_data_expi.strftime('%d/%m/%Y')}.\n\n"
                f"Para continuar usando o sistema, entre em contato com nossa equipe comercial.\n\n"
                f"Atenciosamente,\nEquipe SaveWeb"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destino],
            fail_silently=False,
        )
        logger.info(f"E-mail de expiração enviado para {email_destino} (licença {licenca.slug}).")
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail para {email_destino}: {e}")