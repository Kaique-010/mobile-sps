from django.contrib import admin
from .models import SaidasEstoque

class SaidasEstoqueAdmin(admin.ModelAdmin):
    list_display = ('said_prod', 'said_enti', 'said_tota',  'said_obse')
    list_filter = ( 'said_prod', 'said_tota')

admin.site.register(SaidasEstoque, SaidasEstoqueAdmin)