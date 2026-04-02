
from django.db import models


class Ordemprodfotos(models.Model):
    orpr_codi = models.IntegerField(primary_key=True)  
    orpr_empr = models.IntegerField()
    orpr_fili = models.IntegerField()
    orpr_nume_foto = models.IntegerField()
    orpr_desc_foto = models.TextField(blank=True, null=True)
    orpr_foto_ante = models.BinaryField(blank=True, null=True)
    orpr_foto_atua = models.BinaryField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemprodfotos'
        unique_together = (('orpr_codi', 'orpr_empr', 'orpr_fili', 'orpr_nume_foto'),)


class Ordemproditens(models.Model):
    orpr_codi = models.IntegerField(primary_key=True)
    orpr_empr = models.IntegerField()
    orpr_fili = models.IntegerField()
    orpr_pedi = models.IntegerField()
    orpr_item = models.IntegerField()
    orpr_prod = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemproditens'
        unique_together = (('orpr_empr', 'orpr_fili', 'orpr_pedi', 'orpr_item'),)


class Ordemprodmate(models.Model):
    orpm_orpr = models.IntegerField(primary_key=True)
    orpm_codi = models.IntegerField()
    orpm_prod = models.CharField(max_length=20, blank=True, null=True)
    orpm_quan = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    orpm_unit = models.DecimalField(max_digits=15, decimal_places=5, blank=True, null=True)
    orpm_tota = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_med1 = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_med2 = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_med3 = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_qdme = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_qdmt = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orpm_cust = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_lkst = models.CharField(max_length=6, blank=True, null=True)
    orpm_esto = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_totv = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpm_situ = models.BooleanField(blank=True, null=True, default=False)
    orpm_quantidade = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordemprodmate'
        unique_together = (('orpm_orpr', 'orpm_codi'),)


class Etapa(models.Model):

    etap_codi = models.AutoField(primary_key=True)
    etap_nome = models.CharField(max_length=100)
    etap_situ = models.BooleanField(verbose_name='Ativa ?')
    etap_obse = models.TextField(blank=True, null=True, verbose_name='Observação')
    etap_resa = models.BooleanField(blank=True, null=True, default=False, verbose_name='Retorna Saldo')
    etap_comi = models.IntegerField(blank=True, null=True, choices=[(0, 'Não Comissionado'),
                                                                    (1, 'Comissionado sobre valor'),
                                                                    (2, 'Comissionado sobre peso')], default=0)
    
    etap_ence = models.BooleanField(blank=True, null=True, default=False, verbose_name='Encerra Ordem')

    class Meta:
        managed = False
        db_table = 'etapa'
        
    def __str__(self):
        return str(self.etap_nome)



class Moveetapa(models.Model):
    moet_codi = models.AutoField(primary_key=True)
    moet_orpr = models.ForeignKey('Ordemproducao', models.DO_NOTHING, db_column='moet_orpr')
    moet_dain = models.DateTimeField()
    moet_dafi = models.DateTimeField(blank=True, null=True)
    moet_peso = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    moet_obse = models.TextField(blank=True, null=True)
    moet_etap = models.ForeignKey('Etapa', models.DO_NOTHING, db_column='moet_etap')
    moet_situ = models.BooleanField()
    moet_ouri = models.ForeignKey('Ourives', models.DO_NOTHING, db_column='moet_ouri')

    class Meta:
        managed = False
        db_table = 'moveetapa'

    def __str__(self):
        return str(f"{self.moet_codi} - {self.moet_etap.etap_nome}")
class MoveEtapaPeso(models.Model):
    moet_peso_codi = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    moet_peso_moet = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    moet_peso_prod= models.IntegerField()
    moet_peso_oppr = models.IntegerField()
    moet_peso_sald = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'moveetapeso'
        unique_together = (('moet_peso_codi', 'moet_peso_moet'),)

    def __str__(self):
        return str(self.moet_peso_moet)

class Ourives(models.Model):
    ouri_codi = models.AutoField(primary_key=True)
    ouri_nome = models.CharField(max_length=100)
    ouri_cpfe = models.CharField(max_length=11)
    ouri_situ = models.BooleanField(verbose_name='Ativo ?')
    ouri_empr = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'ourives'

    def __str__(self):
        return str(self.ouri_nome)
class Ordemproducao(models.Model):
    tipo_ordem = [
        ('1', 'Confecção'),
        ('2', 'Conserto'),
        ('3', 'Orçamento'),
        ('4', 'Conserto Relógio'),
    ]
    
    status_ordem = [
        ('0', 'Em Aberto'),
        ('1', 'Em Andamento'),
        ('2', 'Finalizada'),
        ('3', 'Entregue'),
        ('9', 'Cancelada'),
    ]
    
    orpr_codi = models.AutoField(primary_key=True)
    orpr_entr = models.DateTimeField()
    orpr_fech = models.DateTimeField(blank=True, null=True)
    orpr_daen = models.DateTimeField(blank=True, null=True)
    orpr_nuca = models.CharField(unique=True, max_length=6)
    orpr_clie = models.IntegerField()
    orpr_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    orpr_prev = models.DateTimeField()
    orpr_empr = models.IntegerField(db_column='orpr_empr', default=1)
    orpr_fili = models.IntegerField(default=1)
    orpr_tipo = models.CharField(max_length=100, choices=tipo_ordem, default='Confecção')
    orpr_gara = models.BooleanField()
    orpr_vend = models.IntegerField()  
    orpr_desc = models.TextField(blank=True, null=True)
    orpr_stat = models.CharField(max_length=100, choices=status_ordem, default='0')
    orpr_prod = models.CharField(max_length=20, blank=True, null=True)
    orpr_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orpr_gram_clie = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    orpr_cort = models.BooleanField()

    def __str__(self):
        return str(self.orpr_clie)
    

    class Meta:
       
        db_table = 'ordemproducao'



class Ordemproducaoproduto(models.Model):
    orpr_prod_codi = models.AutoField(primary_key=True)
    orpr_prod_orpr = models.ForeignKey('Ordemproducao', models.DO_NOTHING, db_column='orpr_prod_orpr')
    orpr_prod_prod = models.ForeignKey('Produtos.Produtos', models.DO_NOTHING, db_column='orpr_prod_prod')     
    orpr_prod_empr = models.IntegerField()
    orpr_quan_prev = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, verbose_name='Quantidade Prevista')

    class Meta:
        managed = False
        db_table = 'ordemproducaoproduto'
