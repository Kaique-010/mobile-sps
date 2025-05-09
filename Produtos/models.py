from django.db import models
from django.utils.html import mark_safe


class GrupoProduto(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'gruposprodutos'
        verbose_name = 'Grupo de Produto'
        verbose_name_plural = 'Grupos de Produtos'
        managed = 'false'


    def __str__(self):
        return f'{self.codigo} - {self.descricao}'

class SubgrupoProduto(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'subgruposprodutos'
        managed = 'false'



    def __str__(self):
        return self.descricao

class FamiliaProduto(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'familiaprodutos'
        managed = 'false'



    def __str__(self):
        return self.descricao

class Marca(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    nome = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Nome'
    )

    class Meta:
        db_table = 'marca'
        managed = 'false'



    def __str__(self):
        return self.nome

class Tabelaprecos(models.Model):
    tabe_empr = models.IntegerField(primary_key=True, default=1)  
    tabe_fili = models.IntegerField(default=1)
    tabe_prod = models.ForeignKey("Produtos", verbose_name="Produto", on_delete=models.CASCADE, default=1)
    tabe_prco = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_icms = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_vipi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_pipi = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_fret = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_desp = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_cust = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_impo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_apra = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_vare = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True) 
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True) 
    tabe_valo_st = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_perc_reaj = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_hist = models.TextField(blank=True, null=True)
    tabe_cuge = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_entr = models.DateField(blank=True, null=True)
    tabe_perc_st = models.DecimalField(max_digits=7, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = 'tabelaprecos'
        unique_together = (('tabe_empr', 'tabe_fili', 'tabe_prod'),)
        managed = 'false'

class UnidadeMedida(models.Model):
    unid_codi = models.CharField(max_length=10, db_column='unid_codi', primary_key=True) 
    unid_desc = models.CharField(max_length=50, db_column='unid_desc') 
    

    class Meta:
        db_table = 'unidadesmedidas'
        managed = 'false'


    def __str__(self):
        return self.unid_desc


class Produtos(models.Model):
    prod_empr = models.CharField(max_length=50, db_column='prod_empr')
    prod_codi = models.CharField(max_length=50, db_column='prod_codi', primary_key=True) 
    prod_nome = models.CharField(max_length=255, db_column='prod_nome') 
    prod_unme = models.ForeignKey(UnidadeMedida,on_delete=models.PROTECT, db_column='prod_unme') 
    prod_grup= models.ForeignKey(GrupoProduto, on_delete=models.DO_NOTHING, db_column='prod_grup', related_name='produtos', blank= True, null= True) 
    prod_sugr = models.ForeignKey(SubgrupoProduto, on_delete=models.DO_NOTHING, db_column='prod_sugr', related_name='produtos', blank= True, null= True) 
    prod_fami= models.ForeignKey(FamiliaProduto, on_delete=models.DO_NOTHING, db_column='prod_fami', related_name='produtos', blank= True, null= True) 
    prod_loca = models.CharField(max_length=255, db_column='prod_loca', blank= True, null= True) 
    prod_ncm = models.CharField(max_length=10, db_column='prod_ncm') 
    prod_marc = models.ForeignKey(Marca, on_delete=models.DO_NOTHING, db_column='prod_marc', related_name='produtos', blank= True, null= True) 
    prod_coba = models.CharField(max_length=50, db_column='prod_coba', blank= True, null= True)
    prod_foto = models.ImageField(upload_to='fotos/', db_column='prod_foto', blank=True, null=True) 



    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        managed = 'false'

    def __str__(self):
        return self.prod_codi
    
    def imagem_tag(self):
        try:
            return mark_safe(f'<img src="{self.foto.url}" width="80" height="80" />')
        except AttributeError:
            return "Sem foto"

    imagem_tag.short_description = 'Imagem'


class SaldoProduto(models.Model):
    produto_codigo = models.ForeignKey(Produtos, on_delete=models.CASCADE, db_column='sapr_prod')
    empresa = models.CharField(max_length=50, db_column='sapr_empr')
    filial = models.CharField(max_length=50, db_column='sapr_fili')
    saldo_estoque = models.DecimalField(max_digits=10, decimal_places=2, db_column='sapr_sald')

    class Meta:
        db_table = 'saldosprodutos'
        managed = 'false'
        