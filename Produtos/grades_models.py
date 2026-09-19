from django.db import models


class Grade(models.Model):
    grad_empr = models.IntegerField()
    grad_fili = models.IntegerField()
    grad_prod = models.CharField(max_length=20, primary_key=True)
    grad_item = models.IntegerField()
    grad_desc = models.CharField(max_length=40, blank=True, null=True)
    grad_quan = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    grad_entr = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    grad_said = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    grad_sald = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    grad_nume = models.CharField(max_length=15, blank=True, null=True)
    grad_cor = models.CharField(max_length=30, blank=True, null=True)
    grad_volt = models.DecimalField(max_digits=3, decimal_places=0, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'grade'
        unique_together = (('grad_empr', 'grad_fili', 'grad_prod', 'grad_item'),)