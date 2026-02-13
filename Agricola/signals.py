# agricola/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MovimentacaoEstoque
from .service.estoque_service import EstoqueDomainService


@receiver(post_save, sender=MovimentacaoEstoque)
def movimentacao_post_save(sender, instance, created, using, **kwargs):

    if not created:
        return

    EstoqueDomainService.processar_movimentacao(
        instance=instance,
        using=using
    )
