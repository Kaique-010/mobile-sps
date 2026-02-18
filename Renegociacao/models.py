from django.db import models

class Renegociado(models.Model):
    rene_id = models.AutoField(primary_key=True)
    rene_empr = models.IntegerField(blank=True, null=True)
    rene_fili = models.IntegerField(blank=True, null=True)
    rene_clie = models.IntegerField(blank=True, null=True)
    rene_titu = models.CharField(max_length=255, blank=True, null=True)
    rene_seri = models.CharField(max_length=5, blank=True, null=True, default='REN')
    rene_parc = models.CharField(max_length=3, blank=True, null=True)
    rene_venc = models.DateField(blank=True, null=True)
    rene_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    rene_bole = models.CharField(max_length=50, blank=True, null=True)
    rene_perc_mult = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    rene_valo_mult = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    rene_perc_juro = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    rene_valo_juro = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    rene_juro_dia = models.BooleanField(blank=True, null=True)
    rene_dias = models.IntegerField(blank=True, null=True)
    rene_vlfn = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    rene_desc = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    rene_data = models.DateField(blank=True, null=True)
    rene_stat = models.CharField(
        max_length=1,
        choices=[
            ("A", "Ativa"),
            ("Q", "Quebrada"),
            ("C", "Concluída"),
            ("X", "Cancelada"),
        ],
        default="A"
    )
    rene_usua = models.IntegerField(blank=True, null=True)
    rene_obse = models.CharField(max_length=250, blank=True, null=True)
    rene_pai = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, db_column='rene_pai')

    class Meta:
        managed = True
        db_table = 'renegociado'
