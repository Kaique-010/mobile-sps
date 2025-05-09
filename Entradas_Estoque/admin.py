from django.contrib import admin
from .models import EntradaEstoque

class EntradaEstoqueAdmin(admin.ModelAdmin):
    list_display = ('entr_prod', 'entr_enti', 'entr_tota',  'entr_obse')
    list_filter = ('entr_prod', 'entr_tota')

admin.site.register(EntradaEstoque, EntradaEstoqueAdmin)