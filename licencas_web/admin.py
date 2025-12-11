from django.contrib import admin
from .models import LicencaWeb


@admin.register(LicencaWeb)
class LicencaWebAdmin(admin.ModelAdmin):
    list_display = (
        'slug', 'cnpj', 'db_name', 'db_host', 'db_port', 'db_user', 'db_password'
    )
    search_fields = ('slug', 'cnpj', 'db_name', 'db_host', 'db_user', 'db_password')
    list_filter = ('db_host',)

