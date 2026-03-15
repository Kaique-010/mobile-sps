from django.contrib import admin

from .models import NFeDocumento


@admin.register(NFeDocumento)
class NFeDocumentoAdmin(admin.ModelAdmin):
    list_display = ("empresa", "filial", "tipo", "chave", "criado_em")
    search_fields = ("chave",)
    list_filter = ("tipo", "empresa", "filial")
