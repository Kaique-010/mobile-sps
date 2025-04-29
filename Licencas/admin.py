from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuarios, Empresas, Filiais, Licencas

class UsuariosAdmin(UserAdmin):
    model = Usuarios
    list_display = ['usua_nome']
    list_filter = ['usua_nome']
    search_fields = ['usua_nome']
    ordering = ['usua_nome']
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': ('usua_nome', 'password')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {'fields': ('usua_nome', 'password1', 'password2')}),

    )

admin.site.register(Usuarios, UsuariosAdmin)


class EmpresasAdmin(admin.ModelAdmin):
    list_display = ['empr_nome', 'empr_docu']
    search_fields = ['empr_nome', 'empr_docu']
    list_filter = ['empr_nome']

admin.site.register(Empresas, EmpresasAdmin)


class FiliaisAdmin(admin.ModelAdmin):
    list_display = ['empr_nome', 'empr_docu', 'empr_codi']
    search_fields = ['empr_nome', 'empr_docu']
    list_filter = ['empr_nome']
    raw_id_fields = ('empr_codi',)

admin.site.register(Filiais, FiliaisAdmin)


class LicencasAdmin(admin.ModelAdmin):
    list_display = ['lice_docu', 'lice_nome', 'lice_bloq', 'lice_nume_empr', 'lice_nume_fili']
    search_fields = ['lice_docu', 'lice_nome']
    list_filter = ['lice_bloq']
    ordering = ['lice_nome']

admin.site.register(Licencas, LicencasAdmin)
