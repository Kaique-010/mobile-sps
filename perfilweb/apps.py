from django.apps import AppConfig


class PerfilwebConfig(AppConfig):
    name = 'perfilweb'
    def ready(self):
        from django.db.models.signals import post_save, post_delete
        from .models import PermissaoPerfil, PerfilHeranca
        from .services import limpar_cache_perfil

        def _bump_ver(sender, instance, **kwargs):
            limpar_cache_perfil(instance.perf_perf_id if hasattr(instance, 'perf_perf_id') else instance.perf_filho_id)

        post_save.connect(_bump_ver, sender=PermissaoPerfil, weak=False)
        post_delete.connect(_bump_ver, sender=PermissaoPerfil, weak=False)
        post_save.connect(_bump_ver, sender=PerfilHeranca, weak=False)
        post_delete.connect(_bump_ver, sender=PerfilHeranca, weak=False)
