from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ParametrosGerais, ConfiguracaoEstoque, ConfiguracaoFinanceiro
from .utils import limpar_cache_configuracoes
from core.utils import get_licenca_db_config

@receiver(post_save, sender=ConfiguracaoEstoque)
@receiver(post_save, sender=ConfiguracaoFinanceiro)
@receiver(post_save, sender=ParametrosGerais)
def limpar_cache_apos_alteracao(sender, instance, **kwargs):
    """Limpa cache quando configurações são alteradas"""
    # Determinar banco baseado na instância
    banco = instance._state.db or 'default'
    limpar_cache_configuracoes(banco)

@receiver(post_delete, sender=ParametrosGerais)
def limpar_cache_apos_exclusao(sender, instance, **kwargs):
    """Limpa cache quando parâmetros são excluídos"""
    banco = instance._state.db or 'default'
    limpar_cache_configuracoes(banco)