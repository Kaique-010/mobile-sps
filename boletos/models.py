from django.db import models


class Titulosreceber(models.Model):
    titu_empr = models.IntegerField()
    titu_fili = models.IntegerField()
    titu_clie = models.IntegerField()
    # Identificação
    titu_titu = models.CharField(max_length=13)
    titu_seri = models.CharField(max_length=5)
    titu_parc = models.CharField(max_length=3)
    # Datas básicas
    titu_emis = models.DateField(blank=True, null=True)
    titu_venc = models.DateField(blank=True, null=True)
    # Valor
    titu_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    # Nosso número / controle bancário
    titu_noss_nume = models.CharField(max_length=30, blank=True, null=True)
    titu_noss_nume_form = models.CharField(max_length=50, blank=True, null=True)
    # Linha digitável / URL boleto
    titu_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    titu_url_bole = models.CharField(max_length=255, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'titulosreceber'
        

class Remessaretorno(models.Model):
    bole_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bole_obse = models.TextField(blank=True, null=True)
    bole_banc = models.IntegerField(blank=True, null=True)
    bole_cart = models.IntegerField(blank=True, null=True)
    bole_noss = models.CharField(max_length=30, blank=True, null=True)
    bole_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    bole_nome_arqu = models.CharField(max_length=100, blank=True, null=True)
    bole_data_rece = models.DateField(blank=True, null=True)
    bole_valo_rece = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'boleto'


class Boleto(models.Model):
    bole_empr = models.IntegerField()
    bole_fili = models.IntegerField()
    bole_soci = models.CharField(max_length=15)


    bole_titu = models.CharField(max_length=13)
    bole_seri = models.CharField(max_length=3)
    bole_parc = models.CharField(max_length=3)


    bole_emis = models.DateField(blank=True, null=True)
    bole_venc = models.DateField(blank=True, null=True)
    bole_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)


    bole_obse = models.TextField(blank=True, null=True)


    bole_banc = models.IntegerField(blank=True, null=True)
    bole_cart = models.IntegerField(blank=True, null=True)


    bole_noss = models.CharField(max_length=30, blank=True, null=True)


    bole_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    bole_nome_arqu = models.CharField(max_length=100, blank=True, null=True)


    bole_data_rece = models.DateField(blank=True, null=True)
    bole_valo_rece = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'boleto'


class Boletoscancelados(models.Model):
    id = models.IntegerField(primary_key=True)
    linh_digi = models.CharField(max_length=255)
    canc_data = models.DateField(blank=True, null=True)
    canc_moti = models.TextField(blank=True, null=True)
    canc_usua = models.IntegerField(blank=True, null=True)
    canc_nome_usua = models.CharField(max_length=60, blank=True, null=True)
    canc_codi_prot_naci = models.IntegerField(blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'boletoscancelados'
        unique_together = (('id', 'linh_digi'),)


# ====== models/bordero.py ======
from django.utils import timezone


class Bordero(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()


    data = models.DateField(default=timezone.now)
    banco = models.CharField(max_length=4) # Ex: 001, 341, 104
    arquivo_remessa = models.FileField(upload_to="remessas/")
    arquivo_retorno = models.FileField(upload_to="retornos/", null=True, blank=True)


    status = models.IntegerField(choices=[
                                    (0, "Gerado"),
                                    (1, "Enviado"),
                                    (2, "Processado Retorno")
                                    ],
                                    default=0
                                    )


    class Meta:
        db_table = "fin_bordero"


        def __str__(self):
            return f"Bordero {self.id} - Banco {self.banco} - Status {self.get_status_display()}"