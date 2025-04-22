from django.db import models
from Entidades.models import Entidades
from Produtos.models import Produtos

# Create your models here.
class ListaCasamento(models.Model):
    list_empr = models.IntegerField('Empresa')
    list_fili = models.IntegerField('Filial')
    list_nume = models.BigAutoField('Número', primary_key=True)
    list_clie = models.ForeignKey(Entidades, on_delete=models.CASCADE)
    list_data = models.DateField('Data')
    list_stat = models.CharField(
        'Status',
        choices=[
            ('0', 'Aberta'),
            ('1', 'Aguardando cliente'),
            ('2', 'Finalizada'),
            ('3', 'Cancelada'),
        ],
        default='0',
        max_length=1
    )

    class Meta:
        db_table = 'lista_casamento'


class ItensListaCasamento(models.Model):
    item_empr = models.IntegerField(default=1)
    item_fili = models.IntegerField(default=1)
    item_list = models.ForeignKey(ListaCasamento, on_delete=models.CASCADE, related_name='itens', db_column='item_list')
    item_prod = models.ForeignKey(Produtos, on_delete=models.CASCADE, db_column='item_prod')
    item_comp = models.CharField('Complemento', max_length=150, blank=True, null=True)

    class Meta:
        db_table = 'itens_lista_casamento'