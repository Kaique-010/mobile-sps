from django.db import models
from Entidades.models import Entidades
from Produtos.models import Produtos
from Licencas.models import Usuarios


class ListaCasamento(models.Model):
    list_empr = models.IntegerField('Empresa')
    list_fili = models.IntegerField('Filial')
    list_codi = models.AutoField('Número Lista', primary_key=True)
    list_noiv = models.ForeignKey(Entidades, verbose_name='Noiva', on_delete=models.CASCADE, db_column='list_noiv')
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
    list_usua = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column='list_usua')
    log_data = models.DateField(auto_now_add=True)
    log_time = models.TimeField(auto_now_add=True)

    class Meta:
        db_table = 'listacasamento'
        verbose_name = 'Lista de Casamento'
        verbose_name_plural = 'Listas de Casamento'
        managed = False

    @property
    def itens_lista(self):
        return ItensListaCasamento.objects.filter(
        item_empr=self.list_empr,
        item_fili=self.list_fili,
        item_list=self.list_codi
    )

class ItensListaCasamento(models.Model):  
    item_empr = models.IntegerField()
    item_fili = models.IntegerField()
    item_list = models.IntegerField()
    item_item = models.IntegerField(primary_key=True)
    item_prod = models.ForeignKey(Produtos, on_delete=models.CASCADE, db_column='item_prod')
    item_fina = models.BooleanField(default=False)
    item_clie = models.ForeignKey(Entidades, verbose_name='Cliente', on_delete=models.SET_NULL, blank=True, null=True, db_column='item_clie')
    item_pedi = models.IntegerField()
    item_usua = models.ForeignKey(Usuarios, on_delete=models.CASCADE, db_column='item_usua')
    log_data = models.DateField(auto_now_add=True)
    log_time = models.TimeField(auto_now_add=True)

    class Meta:
        db_table = 'itenslistacasamento'
        managed = False
