from django.db import models


class Plano(models.Model):
    plan_nome = models.CharField(max_length=100)
    plan_prec = models.DecimalField(max_digits=6, decimal_places=2)
    plan_desc = models.TextField()
    plan_trial = models.BooleanField(default=False)
    plan_trial_dias = models.IntegerField(default=15)
    plan_data_ativ = models.DateTimeField(null=True, blank=True)
    plan_data_expi = models.DateTimeField(null=True, blank=True)
    plan_ativ = models.BooleanField(default=False)
    
    
    class Meta:
        db_table = 'planos'
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'
        ordering = ['id','plan_nome']
