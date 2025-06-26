from django.db import models


class RecebimentoSdk(models.Model):
    sdk_id = models.AutoField(primary_key=True)
    sdk_empr = models.IntegerField(default=1, verbose_name='Empresa')
    sdk_fili = models.IntegerField(default=1, verbose_name='Filial')
    sdk_pedi = models.IntegerField() 
    sdk_tipo = models.CharField(  
        max_length=10,
        choices=[('pix', 'Pix'), ('debito', 'Débito'), ('credito', 'Crédito')]
    )
    sdk_valo = models.DecimalField(max_digits=10, decimal_places=2) 
    sdk_parc = models.IntegerField(default=1)  
    sdk_stat = models.CharField(max_length=20, default='pendente')  
    sdk_seri = models.CharField(max_length=20, default='SDK')
    sdk_data = models.DateTimeField(auto_now_add=True)   
    sdk_resp = models.CharField(max_length=255, blank=True, null=True)           
    sdk_erro = models.CharField(max_length=255, blank=True, null=True)  
    
    class Meta:
        ordering = ["-sdk_data"]
        unique_together = ('sdk_empr', 'sdk_fili', 'sdk_pedi')
        db_table = "recebimentosdk"

    def __str__(self):
        return f"Recebimento {self.sdk_pedi} - {self.sdk_stat} - {self.sdk_data}"


class TituloReceberSdk(models.Model):
    titu_id = models.AutoField(primary_key=True)
    titu_empr = models.IntegerField(default=1, verbose_name='Empresa')
    titu_fili = models.IntegerField(default=1, verbose_name='Filial')
    titu_rece = models.ForeignKey(RecebimentoSdk, on_delete=models.CASCADE, db_column='titu_rece')
    titu_nume = models.IntegerField() 
    titu_valo = models.DecimalField(max_digits=10, decimal_places=2)
    titu_seri = models.CharField(max_length=20, default='SDK')
    titu_data = models.DateField() 
    titu_stat = models.CharField(max_length=20, default='previsto')  
    
    class Meta:
        ordering = ["titu_data"]
        db_table = "titulosrecebersdk"
        unique_together = ('titu_empr', 'titu_fili', 'titu_rece', 'titu_nume')
        
    def __str__(self):
        return f"Titulo {self.titu_nume} - {self.titu_stat} - {self.titu_data}"
    
    


