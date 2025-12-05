from django.db import models
from django.apps import apps
from django.core.cache import cache
import logging

class Modulo(models.Model):
    modu_codi = models.AutoField(primary_key=True)
    modu_nome = models.CharField(max_length=50, unique=True, help_text="Nome do módulo")
    modu_desc = models.TextField(help_text="Descrição do módulo")
    modu_ativ = models.BooleanField(default=True, help_text="Módulo ativo no sistema")
    modu_icon= models.CharField(max_length=50, blank=True, help_text="Ícone do módulo")
    modu_orde = models.IntegerField(default=0, help_text="Ordem de exibição")

    class Meta:
        db_table = 'modulosmobile'        
        ordering = ['modu_orde', 'modu_nome']

    @classmethod
    def _installed_app_slugs(cls):
        slugs = []
        for app_config in apps.get_app_configs():
            label = app_config.label
            if label.startswith('django') or label in ['rest_framework', 'channels', 'corsheaders', 'debug_toolbar']:
                continue
            slugs.append(label)
        return sorted(set(slugs))

    @classmethod
    def sync_installed_apps(cls, alias='default', force=False):
        logger = logging.getLogger(__name__)
        cache_key = 'installed_app_slugs'
        slugs = None if force else cache.get(cache_key)
        if slugs is None:
            slugs = cls._installed_app_slugs()
            cache.set(cache_key, slugs, 3600)

        created = 0
        updated = 0
        order = 1
        for slug in slugs:
            try:
                obj = cls.objects.using(alias).get(modu_nome=slug)
                changed = False
                if obj.modu_ativ is False:
                    obj.modu_ativ = True
                    changed = True
                if obj.modu_orde != order:
                    obj.modu_orde = order
                    changed = True
                if changed:
                    obj.save(using=alias)
                    updated += 1
            except cls.DoesNotExist:
                obj = cls(
                    modu_nome=slug,
                    modu_desc=f"Módulo {slug}",
                    modu_ativ=True,
                    modu_icon='',
                    modu_orde=order,
                )
                obj.save(using=alias)
                created += 1
            order += 1
        logger.info(f"Sincronização de módulos concluída: {created} criados, {updated} atualizados")
        return {'created': created, 'updated': updated, 'total': len(slugs)}


class PermissaoModulo(models.Model):
    perm_codi = models.AutoField(primary_key=True)
    perm_empr = models.IntegerField(help_text="Código da empresa")
    perm_fili = models.IntegerField(help_text="Código da filial")
    perm_modu = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='permissoes', db_column='perm_modu')
    perm_ativ = models.BooleanField(default=True, help_text="Módulo liberado")
    perm_usua_libe = models.IntegerField(blank=True, help_text="Usuário que liberou")
    perm_data_alte = models.DateTimeField(auto_now=True, help_text="Data de alteração")
    

    class Meta:
        db_table = 'permissoesmodulosmobile'
        unique_together = ('perm_empr', 'perm_fili', 'perm_modu')
        ordering = ['perm_empr', 'perm_fili', 'perm_modu']

    def save(self, *args, **kwargs):
        alias = kwargs.get('using') or getattr(getattr(self, '_state', None), 'db', None) or 'default'
        old_val = None
        if self.pk:
            try:
                old_val = type(self).objects.using(alias).values_list('perm_ativ', flat=True).get(pk=self.pk)
            except Exception:
                pass

        super().save(*args, **kwargs)

        try:
            from django.db import transaction
            from .models import LogParametroSistema
            from django.core.cache import cache
            from core.middleware import get_licenca_slug

            def write_log():
                try:
                    LogParametroSistema.objects.using(alias).create(
                        log_tabe='permissoesmodulosmobile',
                        log_regi=self.perm_codi,
                        log_acao='update' if old_val is not None else 'create',
                        log_valo_ante=old_val,
                        log_valo_novo=self.perm_ativ,
                        log_usua=self.perm_usua_libe or 0,
                    )
                except Exception:
                    try:
                        LogParametroSistema.objects.using('default').create(
                            log_tabe='permissoesmodulosmobile',
                            log_regi=self.perm_codi,
                            log_acao='update' if old_val is not None else 'create',
                            log_valo_ante=old_val,
                            log_valo_novo=self.perm_ativ,
                            log_usua=self.perm_usua_libe or 0,
                        )
                    except Exception:
                        pass

            def invalidate_cache():
                try:
                    slug = get_licenca_slug() or alias
                    cache.delete(f"modulos_licenca_{slug}_{self.perm_empr}_{self.perm_fili}")
                except Exception:
                    pass

            try:
                transaction.on_commit(lambda: (write_log(), invalidate_cache()))
            except Exception:
                write_log()
                invalidate_cache()
        except Exception:
            pass

    @classmethod
    def has_permission(cls, empresa_id, filial_id, modulo_slug, alias='default'):
        try:
            modulo = Modulo.objects.using(alias).get(modu_nome=modulo_slug, modu_ativ=True)
            return cls.objects.using(alias).filter(
                perm_empr=empresa_id,
                perm_fili=filial_id,
                perm_modu=modulo,
                perm_ativ=True,
            ).exists()
        except Modulo.DoesNotExist:
            return False



class ParametroSistema(models.Model):
    para_codi = models.AutoField(primary_key=True)
    para_empr = models.IntegerField(help_text="Código da empresa")
    para_fili = models.IntegerField(help_text="Código da filial")
    para_modu = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='parametros', db_column='para_modu_id')
    para_nome = models.CharField(max_length=50, help_text="Nome do parâmetro")
    para_desc = models.TextField(help_text="Descrição do parâmetro")
    para_valo = models.BooleanField(default=False, help_text="Valor do parâmetro")
    para_ativ = models.BooleanField(default=True, help_text="Parâmetro ativo")
    para_data_alte = models.DateTimeField(auto_now=True, help_text="Data de alteração")
    para_usua_alte = models.IntegerField(blank=True, help_text="Usuário que alterou")

    class Meta:
        db_table = 'parametrosmobile'
        unique_together = ('para_empr', 'para_fili', 'para_modu', 'para_nome')
        ordering = ['para_modu', 'para_nome']


class LogParametroSistema(models.Model):
    log_codi = models.AutoField(primary_key=True)
    log_tabe = models.CharField(max_length=50, help_text="Tabela alterada")
    log_regi = models.IntegerField(help_text="ID do registro")
    log_acao = models.CharField(max_length=20, choices=[
        ('create', 'Criação'),
        ('update', 'Alteração'),
        ('delete', 'Exclusão')
    ])
    log_valo_ante = models.BooleanField(null=True, blank=True, help_text="Valor anterior")
    log_valo_novo = models.BooleanField(null=True, blank=True, help_text="Valor novo")
    log_usua = models.IntegerField(help_text="Usuário")
    log_data = models.DateTimeField(auto_now_add=True)
    log_ip = models.GenericIPAddressField(blank=True, null=True, help_text="IP do usuário")

    class Meta:
        db_table = 'log_parametro_sistema'
        verbose_name = 'Log de Parâmetro'
        verbose_name_plural = 'Logs de Parâmetros'
        ordering = ['-log_data']

    def __str__(self):
        return f"{self.log_acao} - {self.log_tabe} ({self.log_data})"
