from django.db import models


class Situacoes(models.Model):
    situ_codi = models.IntegerField(primary_key=True)
    situ_nome = models.CharField(max_length=60)
    situ_obse = models.TextField(blank=True, null=True)
    situ_nao_list = models.BooleanField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  
    situ_nao_list_cp = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'situacoes'
