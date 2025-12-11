from django.contrib import admin
from .models import Modulo, PermissaoModulo, ParametroSistema

@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('modu_nome', 'modu_desc', 'modu_ativ', 'modu_icon', 'modu_orde')
    list_filter = ('modu_ativ',)
    search_fields = ('modu_nome', 'modu_desc')
    ordering = ('modu_orde', 'modu_nome')

    actions = ['sincronizar_modulos', 'sincronizar_todas_licencas']

    def sincronizar_modulos(self, request, queryset):
        Modulo.sync_installed_apps(force=True)
    sincronizar_modulos.short_description = 'Sincronizar com apps instalados'

    def sincronizar_todas_licencas(self, request, queryset):
        try:
            from core.licenca_context import get_licencas_map
            from core.dbtools import get_db_from_slug
            Modulo.sync_installed_apps(force=True)
            for lic in get_licencas_map():
                alias = get_db_from_slug(lic.get('slug')) or 'default'
                Modulo.sync_installed_apps(alias=alias, force=True)
        except Exception:
            Modulo.sync_installed_apps(force=True)
    sincronizar_todas_licencas.short_description = 'Sincronizar apps em TODAS as licenças'

@admin.register(PermissaoModulo)
class PermissaoModuloAdmin(admin.ModelAdmin):
    list_display = ('perm_empr', 'perm_fili', 'perm_modu', 'perm_ativ', 'perm_usua_libe', 'perm_data_alte')
    list_filter = ('perm_ativ', 'perm_empr', 'perm_fili')
    search_fields = ('perm_modu__modu_nome',)
    autocomplete_fields = ('perm_modu',)

@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ('para_empr', 'para_fili', 'para_modu', 'para_nome', 'para_ativ', 'para_valo', 'para_data_alte')
    list_filter = ('para_ativ', 'para_empr', 'para_fili')
    search_fields = ('para_nome', 'para_desc', 'para_modu__modu_nome')
    autocomplete_fields = ('para_modu',)
